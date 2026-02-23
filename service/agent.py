import logging
import re
import asyncio
from typing import List, Optional
from pathlib import Path

from config import configer
from models import ChatMessage
from schemas.notebook import TransformationRequest, SourceSummary, TransformationResponse
from .openai import get_openai_service
from .gemini import get_gemini_service
from utils import logger
from models.source import Source
from .prompt import get_transformation_prompt

class Slide:
    """PPT 幻灯片"""
    def __init__(self, style: str, content: str):
        self.style = style
        self.content = content

class NotexAgent:
    def __init__(self):
        self.llm = self._create_llm()
        self.gemini = None

    @staticmethod
    def _create_llm():
        if configer.openai_api_key and configer.openai_base_url:
            return get_openai_service()
        if configer.openai_api_key and not configer.openai_base_url:
            return get_openai_service()
        if configer.google_api_key:
            return get_gemini_service()
        logger.warning("No LLM provider configured. Set OPENAI_API_KEY or GOOGLE_API_KEY.")
        return None

    async def _call_deepinsight(self, summary: str) -> str:
        """调用 DeepInsight 外部工具（对应 Go 的 callDeepInsight）"""
        # 创建临时文件
        tmp_dir = Path("./data/tmp")
        tmp_dir.mkdir(parents=True, exist_ok=True)
        tmp_file = tmp_dir / f"deepinsight_report_{int(asyncio.get_event_loop().time() * 1000)}.md"
        try:
            # 执行 DeepInsight 命令
            proc = await asyncio.create_subprocess_exec(
                "./DeepInsight",
                "-o", str(tmp_file),
                summary,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=600)

            if proc.returncode != 0:
                error_msg = stderr.decode() if stderr else ""
                raise RuntimeError(f"DeepInsight command failed: {error_msg}")

            # 读取生成的报告
            report_content = tmp_file.read_text(encoding="utf-8")
            return report_content

        except asyncio.TimeoutError:
            raise RuntimeError("DeepInsight command timeout after 10 minutes")
        except Exception as e:
            logger.error(f"DeepInsight execution failed: {e}")
            raise
        finally:
            # 清理临时文件
            if tmp_file.exists():
                tmp_file.unlink()

    def parse_ppt_slides(self, content: str) -> List[Slide]:
        """解析 PPT 幻灯片（对应 Go 的 ParsePPTSlides）"""
        slides = []

        # 1. 提取风格指令
        style = ""
        style_start = content.find("<STYLE_INSTRUCTIONS>")
        style_end = content.find("</STYLE_INSTRUCTIONS>")
        if style_start != -1 and style_end > style_start:
            style = content[style_start + 20:style_end]

        # 2. 按 Slide 标记分割
        pattern = re.compile(r'^(?:\s*#{1,6}\s*)?(?:Slide|幻灯片|第\d+张幻灯片|##)\s*\d+[:\s]*.*$', re.MULTILINE)
        matches = list(pattern.finditer(content))

        if matches:
            for i, match in enumerate(matches):
                start = match.start()
                end = len(content) if i + 1 >= len(matches) else matches[i + 1].start()

                slide_content = content[start:end]

                # 验证：必须包含至少一个必需字段
                lower = slide_content.lower()
                if any(keyword in lower for keyword in ["叙事目标", "narrative goal", "关键内容"]):
                    slides.append(Slide(style=style, content=slide_content))

        # 3. 如果没找到，尝试按 "// 叙事目标" 分割
        if not slides:
            marker = "// 叙事目标"
            if marker not in content:
                marker = "// NARRATIVE GOAL"

            if marker in content:
                parts = content.split(marker)
                for i in range(1, len(parts)):
                    slides.append(Slide(style=style, content=marker + parts[i]))

        # 最终 fallback
        if not slides:
            slides.append(Slide(style=style, content=content))

        return slides

    async def generate_chat(self, notebook_id: str, message: str, history: list[ChatMessage], context: str) ->str:

        msg_limit = 10
        context_msg = []

        # 1. 添加历史消息（限制数量）
        for msg in history[-msg_limit:]:
            context_msg.append({"role": msg.role, "content": msg.content})

        # 2. 添加知识库消息
        if context and context.strip():
            context_msg.append({"role": "user", "content": f"请根据以下来源内容来回答用户的问题：\n\n{context}"})

        result = await self.llm.generate_chat(message, context_msg)

        return result

    async def generate_transformation(self, req: TransformationRequest, sources: list[Source]) -> TransformationResponse:
        source_context = ""
        for i, src in enumerate(sources):
            source_context += f"\n## Source {i}: {src.name}\n"
            limit = 100000 if configer.max_sources <= 0 else configer.max_sources
            if src.content != "":
                if len(src.content) <= limit:
                    source_context += src.content
                else:
                    source_context += src.content[:limit]
                    source_context += f"\n... [Content truncated, total length: {len(src.content)}]"
            else:
                source_context += f"[Source content: {src.name}, type: {src.type}]"

            source_context += "\n"

        prompt_template = get_transformation_prompt(req.type)
        prompt = prompt_template.format(
            sources=source_context,
            type=req.type,
            length=req.length,
            format=req.format,
            prompt=req.prompt or ""
        )

        # 根据类型选择生成方式
        if req.type == "ppt":
            if self.gemini:
                response = await self.gemini.generate_text(prompt, "gemini-2.0-flash-exp")
            else:
                response = await self.llm.generate_text(prompt)
        elif req.type == "insight":
            # 先生成摘要
            summary = await self.llm.generate_text(prompt)
            # 尝试调用 DeepInsight，如果不可用则使用 LLM 生成深度分析
            try:
                response = await self._call_deepinsight(summary)
            except FileNotFoundError:
                logging.warning("DeepInsight CLI not found, using LLM for insight generation")
                # 使用 LLM 生成深度洞察
                insight_prompt = f"""基于以下摘要，生成一份深度洞察报告。

        摘要内容：
        {summary}

        请生成一份包含以下内容的深度洞察报告：
        1. 核心发现和关键洞察
        2. 数据趋势和模式分析
        3. 潜在问题和风险
        4. 机会识别和建议
        5. 战略性思考和建议

        报告应该具有深度和前瞻性，提供独特的视角和见解。使用中文输出。"""
                response = await self.generate_text(insight_prompt)
            except Exception as e:
                logging.error(f"DeepInsight execution failed: {e}, falling back to LLM")
                # 发生其他错误也回退到 LLM
                insight_prompt = f"基于以下内容生成深度洞察报告：\n\n{summary}"
                response = await self.generate_text(insight_prompt)
        else:
            # 直接 LLM 生成
            response = await self.generate_text(prompt)

        # 构建 source summaries
        source_summaries = [
            SourceSummary(id=src.id, name=src.name, type=src.type)
            for src in sources
        ]

        return TransformationResponse(
                type=req.type,
                content=response,
                sources=source_summaries,
                metadata={"length": req.length, "format": req.format}
        )

    async def generate_text(self, prompt: str) -> str:

        response = await self.llm.generate_text(prompt)

        return response

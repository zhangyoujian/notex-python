import os
import aiofiles
import aiofiles.os
import asyncio
from config import configer
import uuid


def needs_markitdown(ext: str) -> bool:
    """判断是否需要 markitdown 转换"""
    markitdown_exts = {".pdf", ".docx", ".doc", ".pptx", ".ppt", ".xlsx", ".xls"}
    return ext in markitdown_exts


async def convert_with_markitdown(file_path: str) -> str:
    """异步调用 markitdown 命令行转换文档为 Markdown"""
    tmp_file = os.path.join(os.path.dirname(file_path), f"__markitdown_{os.path.basename(file_path)}.md")
    cmd = [configer.markitdown_cmd, file_path, "-o", tmp_file]
    process = await asyncio.create_subprocess_exec(*cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    stdout, stderr = await process.communicate()
    if process.returncode != 0:
        raise RuntimeError(f"markitdown failed: {stderr.decode()}")
    async with aiofiles.open(tmp_file, "r", encoding="utf-8") as f:
        content = await f.read()
    await aiofiles.os.remove(tmp_file)  # 同步删除，可改用 aiofiles 异步删除
    return content


async def extract_from_file( path: str) -> str:
    """读取本地文件，若需转换则调用 markitdown"""
    ext = os.path.splitext(path)[1].lower()
    if configer.enable_markitdown and needs_markitdown(ext):
        return await convert_with_markitdown(path)
    # 普通文本文件异步读取
    async with aiofiles.open(path, "r", encoding="utf-8") as f:
        return await f.read()


async def extract_from_url(url: str) -> str:
    """从 URL 获取内容并转换"""
    if not configer.enable_markitdown:
        raise RuntimeError("markitdown is disabled, cannot fetch URL content")

    tmp_file = f"/tmp/markitdown_url_{uuid.uuid4().hex}.md"
    cmd = [configer.markitdown_cmd, url, "-o", tmp_file]
    process = await asyncio.create_subprocess_exec(*cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    stdout, stderr = await process.communicate()
    if process.returncode != 0:
        raise RuntimeError(f"markitdown URL conversion failed: {stderr.decode()}")
    async with aiofiles.open(tmp_file, "r", encoding="utf-8") as f:
        content = await f.read()
    await aiofiles.os.remove(tmp_file)
    return content

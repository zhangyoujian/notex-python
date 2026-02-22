# Notex

[English](./README.md) | [中文](./README_CN.md)

<p align="center">
  <img src="./docs/note2.png" alt="Notex" width="400"/>
</p>

<p align="center">
  <a href="https://github.com/zhangyoujian/notex-python">
    <img src="https://img.shields.io/github/stars/zhangyoujian/notex-python" alt="stars">
  </a>
  <a href="https://github.com/zhangyoujian/notex-python/LICENSE">
    <img src="https://img.shields.io/github/license/zhangyoujian/notex-python" alt="license">
  </a>
  <a href="https://img.shields.io/badge/Python-3.12+-3776AB?style=flat&logo=python">
    <img src="https://img.shields.io/badge/Python-3.12+-3776AB?style=flat&logo=python" alt="Python Version">
  </a>
  <a href="https://img.shields.io/badge/FastAPI-009688?style=flat&logo=fastapi">
    <img src="https://img.shields.io/badge/FastAPI-009688?style=flat&logo=fastapi" alt="FastAPI">
  </a>
</p>

## 📖 简介

python-notex 是一个**隐私优先**的 AI 知识管理应用，旨在成为 [Google NotebookLM](https://notebooklm.google/) 的开源替代品。


---

## ✨ 特性

### 📚 文档支持
- **多格式支持**：PDF、TXT、Markdown、DOCX、HTML
- **多种导入方式**：文件上传、粘贴文本、URL 抓取
- **智能文档解析**：基于 markitdown 支持复杂文档格式

### 🤖 AI 功能
- **RAG 智能对话**：基于文档内容进行智能问答，支持引用来源
- **向量检索**：Chroma 向量存储，语义搜索更精准
- **12 种内容转换**：

| 转换类型 | 说明 |
|---------|------|
| 📝 Summary | 综合摘要 |
| ❓ FAQ | 常见问题解答 |
| 📚 Study Guide | 学习指南 |
| 🗂️ Outline | 结构化大纲 |
| 🎙️ Podcast | 播客脚本 |
| 📅 Timeline | 时间线 |
| 📖 Glossary | 术语表 |
| ✍️ Quiz | 测验题目 |
| 🧠 Mindmap | Mermaid 思维导图 |
| 📊 Infographic | 信息图（需 Gemini） |
| 📑 PPT | 幻灯片（需 Gemini） |
| 💡 Insight | 深度洞察报告 |

### 🔒 隐私优先
- **本地存储**：MySQL + Chroma 向量数据库
- **自主选择模型**：支持 OpenAI、Ollama、DeepSeek、通义千问等

### 🎨 界面
- **原生 Web 界面**：响应式设计，专注研究的学术风格
- **完整的认证系统**：支持注册、登录

---

## 🚀 快速开始

### 前置要求

- Python 3.12+
- MySQL 5.7+ (或使用 SQLite)
- LLM API Key（OpenAI）或本地运行 Ollama

### 安装

```bash
# 克隆仓库
git clone https://github.com/zhangyoujian/notex-python.git
cd notex-python

# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate   # Windows

# 安装依赖
pip install -r requirements.txt

# 复制配置示例
cp .env.example .env

# 编辑 .env 配置你的环境变量
```

### 配置 LLM

#### 方式一：使用 OpenAI（云端）

```bash
# .env
OPENAI_API_KEY=sk-your-key-here
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_MODEL=gpt-4o-mini
EMBEDDING_MODEL=text-embedding-3-small
```

#### 方式二：使用 Ollama（本地免费）

```bash
# 先安装 Ollama: https://ollama.com
# 拉取模型: ollama pull llama3.2

# .env
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.2
```

#### 方式三：使用国产模型

```bash
# DeepSeek 示例
OPENAI_API_KEY=sk-your-key
OPENAI_BASE_URL=https://api.deepseek.com/v1
OPENAI_MODEL=deepseek-chat

# 通义千问示例
OPENAI_API_KEY=sk-your-key
OPENAI_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
OPENAI_MODEL=qwen-turbo
```

### 配置数据库

```bash
# 使用 MySQL
MYSQL_URL=mysql+aiomysql://user:password@localhost:3306/notex

# 或使用 SQLite（默认）
# 不设置 MYSQL_URL 则使用 SQLite
```

### 启动服务

```bash
# 启动服务器
python main.py

# 或使用 uvicorn
uvicorn main:app --host 0.0.0.0 --port 8080 --reload
```

访问 [http://localhost:8080](http://localhost:8080)

---

## 📁 项目结构

```
notex-python/
├── main.py                 # FastAPI 应用入口
├── config.py               # 配置管理
├── requirements.txt        # Python 依赖
├── crud/                   # 数据库 CRUD 操作
│   ├── auth.py
│   ├── notebook.py
│   └── ...
├── models/                 # SQLAlchemy 模型
│   ├── base.py
│   ├── user.py
│   ├── notebook.py
│   └── ...
├── routers/                # API 路由
│   ├── auth.py            # 认证相关
│   ├── api.py             # 核心 API
│   ├── files.py           # 文件上传
│   ├── notebooks.py       # 笔记本管理
│   └── ...
├── schemas/                # Pydantic 请求/响应模型
├── service/                # 业务服务
│   ├── database.py        # 数据库连接
│   ├── vector_store.py    # 向量存储 (Chroma)
│   ├── llm.py             # LLM 客户端
│   └── ...
├── frontend/               # 前端页面
├── docs/                   # 文档和图片
└── .env.example            # 配置示例
```

---

## ⚙️ 配置选项

| 变量 | 说明 | 默认值 |
|-----|------|-------|
| `SERVER_HOST` | 服务监听地址 | 0.0.0.0 |
| `SERVER_PORT` | 服务监听端口 | 8080 |
| `OPENAI_API_KEY` | OpenAI API Key | - |
| `OPENAI_BASE_URL` | API 地址 | https://api.openai.com/v1 |
| `OPENAI_MODEL` | 聊天模型 | minimax-m2.5 |
| `EMBEDDING_MODEL` | 向量模型 | text-embedding-3-small |
| `EMBEDDING_MODEL_URL` | 向量模型地址 | http://localhost:8001/v1 |
| `OLLAMA_BASE_URL` | Ollama 地址 | http://localhost:11434 |
| `OLLAMA_MODEL` | Ollama 模型 | llama3.2 |
| `VECTOR_STORE_TYPE` | 向量存储类型 | chroma |
| `VECTOR_STORE_PATH` | Chroma 数据路径 | ./data/chroma_db |
| `MYSQL_URL` | MySQL 连接地址 | - |
| `CHUNK_SIZE` | 文档分块大小 | 1000 |
| `CHUNK_OVERLAP` | 分块重叠大小 | 200 |
| `MAX_SOURCES` | RAG 检索最大来源数 | 5 |
| `GOOGLE_API_KEY` | Gemini API (图片生成) | - |

---

## 📦 技术栈

| 模块 | 技术 |
|------|------|
| Web 框架 | FastAPI |
| 数据库 | MySQL + SQLAlchemy (async) |
| 向量存储 | Chroma |
| LLM | OpenAI SDK |
| 文档解析 | markitdown, PyMuPDF |
| 前端 | 原生 HTML/JS |

---



## 📄 许可证

MIT License - 详见 [LICENSE](./LICENSE)

---

## 🙏 致谢

- 灵感来源：[Google NotebookLM](https://notebooklm.google/)
- 参考项目：[notex](https://github.com/smallnest/notex)

---

## 📞 支持

- 报告问题：[GitHub Issues](https://github.com/zhangyoujian/notex-python/issues)

---

<p align="center">
  Made with ❤️
</p>
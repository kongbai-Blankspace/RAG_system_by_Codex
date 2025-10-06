# 项目说明文档

## 1. 项目简介
RAG_system_by_Codex 是一个集文档管理、向量检索与对话问答为一体的 RAG（Retrieval-Augmented Generation）示例工程，包含：
- **后端**：FastAPI + LangChain/LangGraph，实现文档上传校验、向量索引构建、RAG 对话。
- **前端**：基于 Vite + Vue/TypeScript（见 `frontend/`），提供知识库管理与对话界面。
- **存储**：SQLite（会话、任务、向量库元数据）+ 本地文件系统（文档、FAISS 向量）。

## 2. 目录结构
```
RAG_system_by_Codex/
├── backend/                # FastAPI 服务
│   ├── app/
│   │   ├── api/            # REST 路由
│   │   ├── services/       # 业务逻辑
│   │   ├── models/         # 数据模型 & 数据库
│   │   ├── storage/        # 文档/向量存储
│   │   ├── utils/          # 工具方法
│   │   └── main.py         # 应用入口
│   ├── tests/              # Pytest 集成测试
│   └── 后端开发需求说明.md
├── frontend/               # 前端项目（Vite）
│   ├── src/                # 前端源码
│   ├── openapi.yml         # 后端 OpenAPI 契约
│   └── 我的提示词内容与输出/  # Prompt 设计
├── docs/                   # 项目文档
│   ├── api_testing_guide.md
│   └── project_overview.md
├── .env                    # 示例环境变量
└── README.md               # 快速上手指南
```

## 3. 核心功能流程
1. **文档上传**：后端校验文件扩展名、大小、可解析性，保存校验结果与文件。
2. **向量库构建**：使用 LangChain TextSplitter 切块、Embedding（OpenAI/DeepSeek 或内置 fallback）生成向量，FAISS 本地写盘。
3. **RAG 对话**：
   - 创建会话并存储消息。
   - 根据 `vectorStoreId` 召回上下文。
   - 调用聊天模型生成回答，记录引用片段。
   - 返回消息给前端展示。

整体流程如下：
```
上传文档 → 校验通过 → 构建向量库 → 会话中引用向量库 → 模型回答
```

## 4. 配置与环境
- 使用 `backend/app/config.py` 统一读取设置，支持 `.env`。关键配置：
  - `DATA_DIR` / `DOCUMENT_DIR` / `VECTOR_DIR`：存储目录。
  - `OPENAI_API_KEY` / `DEEPSEEK_API_KEY` / `EMBED_API_KEY`：模型调用凭证。
  - `OPENAI_BASE_URL`：默认通过代理地址，可根据实际服务调整。
  - `ALLOWED_EXTENSIONS`、`MAX_FILE_SIZE_MB`、`MIN_DOCUMENT_LENGTH`：文档限制。
- 启动脚本：`uvicorn app.main:app --host 0.0.0.0 --port 8002`
- 前端可通过 `.env` 或 `vite.config.ts` 配置 API 地址。

## 5. 运行步骤
1. **准备环境**
   - Python 依赖：`pip install -r backend/requirements.txt`（若无，可根据 `backend/app` 中模块自行安装 fastapi、sqlmodel、langchain、langgraph、faiss-cpu 等）。
   - Node 依赖：`cd frontend && npm install`。
2. **启动后端**
   - 在 `backend/` 下运行 `uvicorn app.main:app --reload --port 8002`。
3. **启动前端**
   - `cd frontend && npm run dev`，默认端口 5173，可在 `.env` 中设置后端地址。

## 6. 测试与验证
- **自动化测试**：`pytest backend/tests/test_api.py` 覆盖上传、向量库、聊天主流程。
- **手动测试**：参考 `docs/api_testing_guide.md` 提供的 cURL 示例；前端页面可直接体验 RAG 流程。
- **日志**：后端使用标准 logging，INFO 级别记录关键事件，DEBUG 输出 RAG 统计。可通过设置 `LOGLEVEL=DEBUG` 或启动参数指定。

## 7. 扩展建议
- 将向量库构建与召回迁移至异步/任务队列，提升并发能力。
- 引入鉴权机制（API Key、OAuth）保障接口安全。
- 结合前端开放 conversation 历史搜索、消息引用跳转等功能。
- 基于 LangSmith 或 OpenTelemetry 引入链路追踪，提升可 observability。

## 8. 维护说明
- 任何对后端接口或数据模型的更新需同步修改前端 `openapi.yml` 与 `docs/api_testing_guide.md`。
- 提交前运行 pytest，确保 CI 通过。
- 建议在 README 中记录版本变更历史，便于团队协作。

如有新增模块或依赖，请在 `docs/` 下追加对应说明并在 README 中链接。

# RAG System by Codex

面向企业知识问答场景的端到端 RAG 示例，包含 FastAPI 后端、LangChain/LangGraph 推理流程与 Vite 前端。项目支持文档上传校验、向量库构建、基于检索增强的对话体验，可作为团队二次开发与学习的基础模板。

## ✨ 功能亮点
- 文档上传 + 校验：限制扩展名/大小/文本长度，自动持久化校验结果。
- 向量知识库：基于 FAISS 构建，支持 OpenAI/DeepSeek Embedding，内置 deterministic fallback。
- 对话式 RAG：会话管理、引用召回、模型回答，统一返回引用列表。
- 健康检查与调试日志：便于部署监控与排查。

## 🧱 架构概览
- **后端**：FastAPI、SQLModel、LangChain、LangGraph、FAISS。
- **前端**：Vite + TypeScript（默认使用 Vue 组件库，可自定义）。
- **存储**：SQLite（元数据）+ 本地文件系统（文档与向量）。
- **配置**：Pydantic Settings，支持 `.env` 与环境变量。

详细说明请参考 `docs/project_overview.md`。

## 🚀 快速开始
### 1. 准备环境
```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -U pip
pip install -r backend/requirements.txt  # 如未提供 requirements，可手动安装依赖
```

### 2. 配置 `.env`
```env
OPENAI_API_KEY=your-key-or-test-key
DEEPSEEK_API_KEY=your-key-or-test-key
DATA_DIR=storage/db
DOCUMENT_DIR=storage/documents
VECTOR_DIR=storage/vectors
ALLOWED_EXTENSIONS=.txt,.md,.pdf
MAX_FILE_SIZE_MB=50
MIN_DOCUMENT_LENGTH=200
```

### 3. 启动后端
```bash
cd backend
uvicorn app.main:app --host 0.0.0.0 --port 8002 --reload
```
访问 `http://localhost:8002/docs` 查看 Swagger。

### 4. 启动前端（可选）
```bash
cd frontend
npm install
npm run dev
```
前端默认代理至 `http://localhost:8002`，如需调整请修改 `.env` 或 `vite.config.ts`。

## 🧪 测试
- 后端集成测试：`pytest backend/tests/test_api.py`
- 手工验证：参考 `docs/api_testing_guide.md` 逐个接口测试；前端 UI 可进行集成演练。

## 📁 目录速览
```
backend/        # FastAPI 后端
frontend/       # Vite 前端
docs/           # 项目与接口文档
.env            # 配置示例
```

## ⚙️ 配置与部署
- 默认使用 SQLite，生产环境可替换为云数据库（需接入 SQLModel engine 配置）。
- Embedding/LLM Key 缺失时，系统会使用内置 deterministic 实现，便于离线调试。
- 建议在生产环境开启鉴权、限制 CORS、接入追踪/监控。

## 🤝 贡献指南
1. Fork & Clone 仓库。
2. 基于 `backend/后端开发需求说明.md` 制定需求或变更计划。
3. 提交前运行 `pytest` 与前端构建，确保无回归。
4. 更新文档（`docs/` 与 README）说明功能与用法。

如对项目有疑问或建议，欢迎提交 Issue/PR，一起完善企业级 RAG 解决方案。

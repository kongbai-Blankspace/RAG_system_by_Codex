# 后端接口测试指引

本文档汇总已落地的 REST API，提供测试步骤、示例请求以及期望响应，便于前端或 QA 快速验证功能。

## 1. 运行与基础信息
- 启动命令：`uvicorn app.main:app --host 0.0.0.0 --port 8002`
- 基础 URL：`http://localhost:8002`
- API 前缀：`/api/v1`
- 依赖：确保 `.env` 中配置了必要的目录及模型 Key（无 Key 时仍可运行，系统会使用内置的 deterministic embeddings 和 Fake ChatModel）。

## 2. 快速检查
| 目标 | 方法 | 期望 |
|------|------|------|
| 服务根路由 | `GET /` | `{"message": "RAG backend running", "port": 8002}` |
| 健康检查 | `GET /healthz` | `{"status": "ok", "service": "RAG Backend"}` |

---

## 3. 文档上传模块
### 3.1 上传并校验
- **Endpoint**：`POST /api/v1/documents`
- **请求类型**：`multipart/form-data`
- **字段**：`file`（示例 `sample.md`）
- **cURL 示例**：
  ```bash
  curl -X POST "http://localhost:8002/api/v1/documents"        -F "file=@docs/example.md"
  ```
- **成功响应 (201)**：
  ```json
  {
    "taskId": "<uuid>",
    "status": "success",
    "fileName": "example.md",
    "fileType": "text/markdown",
    "fileSize": 1234,
    "validation": {
      "passed": true,
      "rules": [
        {"rule": "extension", "passed": true, "detail": "allowed: ['.txt', '.md', '.pdf']"},
        {"rule": "size", "passed": true, "detail": "<= 50MB"},
        {"rule": "content_length", "passed": true, "detail": ">= 200 characters"}
      ]
    },
    "message": null,
    "createdAt": "2024-01-01T00:00:00",
    "updatedAt": "2024-01-01T00:00:00"
  }
  ```
- **失败示例 (400)**：扩展名不允许或文本过短均返回
  ```json
  {
    "detail": {
      "code": "DATASET_INVALID",
      "message": "文档校验未通过",
      "issues": [ ... validation rules ... ]
    }
  }
  ```

### 3.2 查询任务状态
- **Endpoint**：`GET /api/v1/documents/{taskId}`
- **cURL**：
  ```bash
  curl "http://localhost:8002/api/v1/documents/<taskId>"
  ```
- **响应**：与创建返回一致。
- **错误**：不存在的 `taskId` 返回 404 + `{ "detail": "Document task not found" }`。

---

## 4. 向量存储模块
### 4.1 创建向量库
- **Endpoint**：`POST /api/v1/vector-stores`
- **依赖**：传入的 `documentTaskId` 必须对应状态 `success` 的任务。
- **请求体**：
  ```json
  {
    "documentTaskId": "<taskId>",
    "config": {
      "name": "示例知识库",
      "chunkSize": 256,
      "overlap": 32,
      "topK": 3
    }
  }
  ```
- **响应 (202)**：
  ```json
  {
    "storeId": "<uuid>",
    "taskId": "<uuid>",
    "statusUrl": "/api/v1/vector-stores/<uuid>"
  }
  ```
- **错误**：
  - 404：文档任务不存在。
  - 400：文档尚未通过校验。

### 4.2 查询向量库
- **Endpoint**：`GET /api/v1/vector-stores/{storeId}`
- **响应**：
  ```json
  {
    "id": "<storeId>",
    "name": "示例知识库",
    "status": "ready",
    "documentTaskId": "<taskId>",
    "config": {
      "name": "示例知识库",
      "chunkSize": 256,
      "overlap": 32,
      "topK": 3
    },
    "createdAt": "2024-01-01T00:00:00",
    "updatedAt": "2024-01-01T00:00:00",
    "failureReason": null
  }
  ```

### 4.3 构建任务状态
- **Endpoint**：`GET /api/v1/vector-stores/{storeId}/tasks/{taskId}`
- **用途**：当前用于前端轮询；`progress` 为 1.0 表示完成，其余为 0.5。

### 4.4 召回片段
- **Endpoint**：`POST /api/v1/vector-stores/{storeId}/recall`
- **请求**：
  ```json
  {
    "query": "LangChain 是什么",
    "topK": 2,
    "withContent": true
  }
  ```
- **响应**：
  ```json
  {
    "storeId": "<storeId>",
    "items": [
      {
        "id": "<storeId>-1",
        "title": "source.md",
        "similarity": 0.42,
        "content": "……原文片段……",
        "metadata": {
          "source": "source.md"
        }
      }
    ]
  }
  ```
- 若 `withContent` 为 false，`content` 为前 100 字符的摘要。
- 若向量库不存在返回 404；召回异常时返回 500 并记录日志。

---

## 5. 会话与聊天模块
### 5.1 创建会话
- **Endpoint**：`POST /api/v1/chat/sessions`
- **请求**：`{"title": "测试对话"}`（可为空）
- **响应**：`{"id": "<sessionId>", "title": "测试对话", "createdAt": "…", "updatedAt": "…"}`

### 5.2 分页查询会话
- **Endpoint**：`GET /api/v1/chat/sessions?page=1&page_size=20`
- **响应**：
  ```json
  {
    "items": [ {"id": "…", "title": "…", "createdAt": "…", "updatedAt": "…"} ],
    "page": 1,
    "pageSize": 20,
    "total": 1
  }
  ```

### 5.3 获取会话详情
- **Endpoint**：`GET /api/v1/chat/sessions/{sessionId}`
- **响应**：
  ```json
  {
    "session": {"id": "…", "title": "…", "createdAt": "…", "updatedAt": "…"},
    "messages": [
      {"id": "…", "role": "user", "content": "…", "timestamp": "…", "citations": []},
      {"id": "…", "role": "assistant", "content": "…", "timestamp": "…", "citations": []}
    ]
  }
  ```

### 5.4 删除会话
- **Endpoint**：`DELETE /api/v1/chat/sessions/{sessionId}`
- **响应**：204 无内容。

### 5.5 发送消息（RAG 推理）
- **Endpoint**：`POST /api/v1/chat/sessions/{sessionId}/messages`
- **请求**：
  ```json
  {
    "message": "你好",
    "vectorStoreId": "<storeId>"  // 可选
  }
  ```
- **响应**：
  ```json
  {
    "sessionId": "<sessionId>",
    "message": {
      "id": "<messageId>",
      "role": "assistant",
      "content": "您好，目前没有命中文档，不过我可以回答常见问题…",
      "timestamp": "2024-01-01T00:00:00",
      "citations": []
    }
  }
  ```
- 日志会输出 `INFO app.services.chat: Chat answer generated…` 及 DEBUG 统计，便于排查。
- 当模型返回空内容时，系统会回退到提示语 `[GraphMissingAnswer] 模型没有返回内容`（正常情况下不应再出现）。

---

## 6. 常见测试流程
1. **上传文档**：使用 >200 字符的 txt/md 文件；记下 `taskId`。
2. **构建向量库**：调用 `POST /vector-stores`，获取 `storeId`，可立即召回验证。
3. **开启会话**：创建新会话、发送消息，若传入 `vectorStoreId` 应在回答中体现引用的知识。
4. **异常分支**：
   - 上传 `.exe` 或过小文件 → 400。
   - 使用无效 `storeId` 调用召回 → 404。
   - 删除会话后再次查询 → 404。

## 7. 测试建议
- 使用 `pytest backend/tests/test_api.py` 可自动化跑完上述流程（需先安装依赖）。
- 如需模拟真实 LLM，把 `.env` 中的 `OPENAI_API_KEY` 或 `DEEPSEEK_API_KEY` 替换为有效值。
- 开启 `LOGLEVEL=DEBUG`（或运行前设置 `uvicorn app.main:app --reload --log-level debug`）可查看 RAG 调试信息。

---

文档更新时请同步检查接口示例，确保与最新代码保持一致。

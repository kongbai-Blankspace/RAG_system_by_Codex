# RAG 本地知识库问答引擎 · 前端说明

> 本仓库是“RAG 本地知识库问答引擎”的前端实现，提供多会话聊天、文档上传建库、召回测试等功能。本文档旨在帮助新同学快速理解架构、功能细节、运行部署与扩展方式。

---

## 目录
1. [项目综述](#项目综述)
2. [系统架构](#系统架构)
3. [技术栈与依赖](#技术栈与依赖)
4. [文件结构](#文件结构)
5. [核心功能说明](#核心功能说明)
6. [设计与交互规范](#设计与交互规范)
7. [环境要求](#环境要求)
8. [快速开始](#快速开始)
9. [配置说明](#配置说明)
10. [开发与调试](#开发与调试)
11. [部署指南](#部署指南)
12. [测试策略与质量保障](#测试策略与质量保障)
13. [常见问题与故障排除](#常见问题与故障排除)
14. [后续扩展建议](#后续扩展建议)

---

## 项目综述
- **产品定位**：桌面 Web 前端，配合 LangGraph 等后端组件，完成本地知识库的构建、检索与问答。
- **目标用户**：对 RAG 流程有需求的研发、运营、售前同学。
- **使用场景**：上传内部资料 → 构建向量库 → 测试召回效果 → 对话问答。
- **体验目标**：新人 10–15 分钟完成搭建；核心流程具备 Loading / 成功 / 失败反馈，降低联调成本。

---

## 系统架构
```text
┌────────────────────────────────────────────────────────────┐
│                      React + Vite SPA                       │
│                                                            │
│  App.tsx (主页面)                                           │
│    ├─ 状态管理：React Hooks （会话 / 文档 / 向量库 / Modal） │
│    ├─ UI 组件：聊天区、知识库面板、上传与配置弹窗             │
│    └─ 数据层：内置 Mock，后续可替换为真实 API 调用            │
│                                                            │
│  Modal 组件：通用弹窗 + 背景遮罩 + ESC 关闭                 │
│  样式层：App.css / index.css（深色商务主题）                 │
└────────────────────────────────────────────────────────────┘
```

### 数据流示意
```
上传文件 → setSelectedFileName → 配置弹窗 → 保存 → setProcessingState → 成功/失败弹窗
召回测试 → handleRecallSubmit → 过滤 mockDocuments → recallResults → 列表 + 详情弹窗
聊天对话 → handleSendMessage → conversations → chatWithCitations → 聊天 UI
引用弹窗 → setSelectedDoc(state) → Modal 展示完整片段
```

---

## 技术栈与依赖
| 类别 | 选型 | 说明 |
|------|------|------|
| 框架 | React 18 | 函数式组件 + Hooks |
| 构建 | Vite 5 | 极速开发服务与打包 |
| 语言 | TypeScript 5 | 严格模式，便于类型约束 |
| 样式 | 纯 CSS | 深色渐变 + Glassmorphism |
| 组件库 | 自研 | Modal / 卡片 / 按钮；便于按需定制 |

主要依赖（见 `package.json`）：`react`, `react-dom`, `@vitejs/plugin-react`, `vite`, `typescript`。

---

## 文件结构
```text
frontend/
├─ dist/                          # 构建产物
├─ node_modules/
├─ src/
│  ├─ App.tsx                     # 业务主体（状态、UI、Mock 数据）
│  ├─ App.css                     # 主题、布局、滚动条样式
│  ├─ index.css                   # 全局基础样式 & CSS 变量
│  ├─ main.tsx                    # React 入口
│  └─ components/
│     └─ Modal.tsx / Modal.css    # 通用模态框组件
├─ index.html                     # Vite HTML 模板
├─ package.json / package-lock.json
├─ tsconfig.json / tsconfig.node.json
└─ vite.config.ts                 # 构建与插件配置
```

---

## 核心功能说明
1. **会话管理**
   - 左侧标签列出全部会话，支持新增、切换、删除。
   - 当前会话的消息在中间区域展示；助手回复附带引用片段按钮。
2. **文档上传与向量库配置**
   - 上传单个文件（txt/md/pdf），进入参数配置弹窗。
   - 可设置向量库名称、Chunk Size、Overlap、TopK；提交后有 Loading → 成功/失败弹窗。
3. **召回测试**
   - 右侧面板输入查询语句，根据 TopK 返回片段摘要、相关性数值。
   - 点击列表项打开详情，展示完整片段内容。
4. **交互闭环**
   - Modal 拉起与关闭；发送按钮在输入框为空时禁用，避免空消息。
   - Loading 动画、空态提示和错误反馈（目前使用 alert）维护用户感知。

---

## 设计与交互规范
- **视觉风格**：
  - 背景：深蓝渐变 + 模糊投影。
  - 主按钮：`#1a9af7→#2563eb` 渐变；禁用状态为灰蓝。
  - 文本：主色 `#e2e8f0`，次级 `#94a3b8`。
- **交互细节**：
  - 滚动区域独立（历史栏 / 对话区）。
  - Modal ESC 关闭、点击遮罩关闭。
  - 键盘可达性：Tab 顺序按视觉布局，Enter 可触发按钮。

---

## 环境要求
| 项目 | 要求 |
|------|------|
| Node.js | ≥ 18.17 |
| 包管理器 | npm 9+（或 pnpm/yarn）|
| 操作系统 | Windows / macOS / Linux |

---

## 快速开始
```bash
# 1. 安装依赖
npm install

# 2. 本地开发
npm run dev
# 打开 http://localhost:5173

# 3. 构建生产版本
npm run build

# 4. 预览生产包 (模拟线上环境)
npm run preview
```

**常见报错**
- Node 版本过低：升级到 Node ≥18 或使用 `nvm use 18`。
- 端口冲突：`npm run dev -- --port 5174`。
- 页面空白 + Hook 错误：检查 Hook 是否在条件语句或循环中调用。

---

## 配置说明
- **环境变量（示例 `.env.local`）**
  ```bash
  VITE_API_BASE_URL=http://localhost:9000
  VITE_LANGGRAPH_ENDPOINT=http://localhost:8000
  ```
- **向量库配置结构**
  ```ts
  interface VectorStoreConfig {
    name: string;
    chunkSize: number;
    overlap: number;
    topK: number;
  }
  ```
- **文档片段结构**
  ```ts
  interface DocumentSnippet {
    id: string;
    title: string;
    similarity: number;
    content: string;
  }
  ```
- **消息结构**
  ```ts
  interface ChatMessage {
    id: number;
    role: 'user' | 'assistant';
    content: string;
    timestamp: string;
    citations?: string[];
    fromRetrieval?: boolean;
  }
  ```

---

## 开发与调试
- 使用 Vite dev server，支持 HMR。
- React Developer Tools 可查看状态；Console/Network 检查 Mock 数据。
- 建议为 API 增加服务层：创建 `src/services`，封装 fetch/axios，统一错误提示。

---

## 部署指南
### 静态托管
```bash
npm run build
npx serve dist   # 或部署到任意静态服务器
```

### Vercel / Netlify
- Build：`npm run build`
- Output：`dist`
- 可通过 UI 配置自定义环境变量。

### GitHub Pages（示例 workflow）
```yaml
name: deploy
on: push
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: 18
      - run: npm ci
      - run: npm run build
      - uses: peaceiris/actions-gh-pages@v3
        with:
          github_token: ${{ secrets.GITHUB_TOKEN }}
          publish_dir: ./dist
```

### Docker + Nginx
```dockerfile
FROM node:18-alpine AS build
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . ./
RUN npm run build

FROM nginx:1.25-alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY deploy/nginx.conf /etc/nginx/conf.d/default.conf
```
`docker-compose.yml`
```yaml
services:
  rag-frontend:
    build: .
    ports:
      - "8080:80"
    environment:
      - VITE_API_BASE_URL=http://backend:9000
```

---

## 测试策略与质量保障
| 项目 | 当前状态 | 建议 |
|------|----------|------|
| Lint/Format | 暂未配置 | 引入 ESLint + Prettier，统一风格 |
| 单元测试 | 暂未配置 | 使用 Vitest + React Testing Library 覆盖上传、召回、聊天逻辑 |
| E2E | 暂未配置 | 采用 Playwright 模拟完整流程 |
| 性能/可访问性 | 手动检查 | 建议使用 Lighthouse 定期评估 |

---

## 常见问题与故障排除
| 问题 | 现象 | 解决方案 |
|------|------|----------|
| Node 版本不匹配 | `ERR_OSSL_EVP_UNSUPPORTED` 等 | 升级 Node ≥18 / 开启 `--openssl-legacy-provider`（不推荐） |
| 端口占用 | `Port 5173 is already in use` | 指定新端口或关闭占用进程 |
| 样式不生效 | 页面结构正常但无样式 | 重启 dev server 或检查 CSS 是否被覆盖 |
| 构建失败 | Memory error | `NODE_OPTIONS=--max_old_space_size=4096 npm run build` |
| 模态无法关闭 | ESC 失效 | 确认 `Modal.tsx` 中 `onClose` 逻辑未被删除 |

---

## 后续扩展建议
- 接入真实 API：在 `src/services` 创建请求层，并参考 `openapi.yml` 统一数据结构。
- 状态管理升级：如业务复杂，考虑引入 Zustand/Recoil，或使用 React Query 管理接口缓存。
- 国际化与权限：使用 i18n 库、路由守卫等方式满足更多场景。
- UI 组件抽象：拆分按钮、面板组件，提升复用性与主题切换能力。

如需进一步支持，欢迎在项目 issue 中补充需求或反馈问题 🙌

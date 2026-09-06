# KB-Graph — 企业 AI 知识库

基于 **GraphRAG 知识图谱** 与 **团队协同 + AI 双驱动** 的新一代企业知识管理平台。

## 核心特色

1. **知识图谱可视化（GraphRAG）**
   - AI 自动从文档抽取实体与关系，构建交互式力导向图（AntV G6 v5）
   - 点击节点跳转关联文档，图谱探索与问答联动
   - 问答时混合检索：向量相似度 + 图邻居扩展，跨文档问题显著更优

2. **团队协作 + AI 双驱动**
   - Yjs CRDT 多人实时协同编辑（互见光标）
   - 评论与通知系统
   - 文档入库后 AI 自动生成摘要、标签与关联推荐

3. **更多**
   - 全文 + 向量（pgvector/HNSW）混合搜索
   - AI 流式问答（SSE），支持引用来源
   - 基于角色的空间权限（owner / admin / member）
   - 多格式文档解析：PDF、DOCX、Markdown、TXT

## 技术栈

| 层级 | 技术 |
|------|------|
| 前端 | Vue 3 + TypeScript + Vite + Pinia + Element Plus + TipTap/Yjs + AntV G6 v5 |
| 后端 | Python FastAPI + SQLAlchemy 2.0 (async) + Celery + Redis |
| 数据库 | PostgreSQL 16 + pgvector（HNSW 索引） |
| AI | OpenAI 兼容 API（DeepSeek / Qwen / Ollama），LLM 与 Embedding 独立配置 |
| 部署 | Docker Compose 一键启动 |

## 项目结构

```
├── frontend/                # Vue 3 + Vite SPA
│   ├── src/
│   │   ├── api/             # HTTP 客户端模块
│   │   ├── components/      # 通用组件（图谱、通知、空状态等）
│   │   ├── layouts/         # 页面布局
│   │   ├── router/          # Vue Router 配置
│   │   ├── stores/          # Pinia 状态管理
│   │   ├── styles/          # 全局样式（CSS 变量、重置、过渡）
│   │   ├── views/           # 页面组件（登录、空间、文档、知识图谱、AI 问答）
│   │   └── __tests__/       # 前端测试（Vitest）
│   ├── Dockerfile
│   └── nginx.conf
├── backend/
│   ├── app/
│   │   ├── api/v1/          # REST API 端点（认证、空间、文档、图谱、聊天、搜索、评论等）
│   │   ├── core/            # 配置、安全、依赖注入
│   │   ├── db/              # 数据库会话
│   │   ├── models/          # SQLAlchemy ORM 模型
│   │   ├── schemas/         # Pydantic 校验
│   │   ├── services/        # 业务逻辑（LLM、Embedding、RAG、实体抽取、解析、分块）
│   │   ├── tasks/           # Celery 异步任务（向量化、图谱抽取、摘要生成）
│   │   └── ws/              # WebSocket（协同编辑）
│   ├── tests/               # 后端测试（pytest）
│   ├── alembic/             # 数据库迁移
│   └── Dockerfile
├── docker-compose.yml       # 完整编排
├── Makefile                 # 常用命令
├── .env.example             # 环境变量模板
└── .gitattributes           # 换行符规范化
```

## 快速开始（Docker）

```bash
git clone <repo-url> && cd kb-graph
cp .env.example .env          # 编辑 .env 填入 LLM / Embedding API Key
docker compose up -d --build
docker compose exec backend alembic upgrade head
# 前端：http://localhost
# 后端 API 文档：http://localhost:8000/docs
```

## 本地开发

**前置条件：** PostgreSQL 16 + pgvector 扩展、Redis（可选，缺省降级为进程内模式）、Python 3.13+、Node.js 20+

### 后端

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # macOS / Linux
pip install -r requirements-dev.txt
cp ../.env.example .env         # 配置 API Key
uvicorn app.main:app --reload --port 8000
```

### 前端

```bash
cd frontend
npm install
npm run dev                     # http://localhost:5173
```

### 常用命令

```bash
make up          # Docker Compose 启动
make down        # Docker Compose 停止
make migrate     # 运行数据库迁移
make test        # 运行后端测试
make seed        # 创建演示数据
```

## 测试

```bash
# 后端
cd backend && python -m pytest                  # 单元 + API 测试
python -m pytest -m integration                 # 集成测试（需真实 LLM/Embedding）

# 前端
cd frontend && npm test                         # Vitest 单元测试
```

## API 文档

后端运行后访问：

- Swagger UI：http://localhost:8000/docs
- ReDoc：http://localhost:8000/redoc

## 环境变量

见 `.env.example`，关键配置：

| 变量 | 说明 |
|------|------|
| `LLM_BASE_URL` | LLM API 地址（DeepSeek / Qwen / Ollama） |
| `LLM_API_KEY` | LLM API 密钥 |
| `LLM_MODEL` | 模型名称（默认 `deepseek-chat`） |
| `EMBEDDING_BASE_URL` | Embedding API 地址（留空则使用哈希回退，仅开发测试） |
| `EMBEDDING_MODEL` | Embedding 模型（默认 `bge-m3`） |
| `DATABASE_URL` | PostgreSQL 连接串 |
| `REDIS_URL` | Redis 连接串 |

## License

MIT

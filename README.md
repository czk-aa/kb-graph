# KB-Graph 企业知识库

带**知识图谱可视化**与**团队协同/AI 双驱动**特色的企业级 AI 知识库。

## 核心特色

1. **知识图谱可视化（GraphRAG）**：AI 自动从文档抽取实体与关系，力导向图交互探索，点击节点跳转关联文档；问答时向量检索 + 图邻居扩展混合召回，跨文档问题显著更优。
2. **团队协作 + AI 双驱动**：Yjs CRDT 多人实时协同编辑（互见光标）、评论与通知；文档入库后 AI 自动生成摘要、标签与关联推荐。

## 技术栈

- 前端：Vue3 + TypeScript + Vite + Pinia + Element Plus + TipTap/Yjs + AntV G6
- 后端：Python FastAPI + SQLAlchemy 2.0 (async) + Celery + Redis
- 数据：PostgreSQL 16 + pgvector（向量检索）、关系表存图
- AI：OpenAI 兼容 API（DeepSeek/Qwen/Ollama），Embedding 独立配置
- 部署：Docker Compose

## 快速开始（Docker）

```bash
cp .env.example .env       # 填入 LLM/Embedding 的 API Key
docker compose up -d --build
docker compose exec backend alembic upgrade head
# 打开 http://localhost
```

## 本地开发

```bash
# 后端
cd backend
python -m venv .venv && .venv\Scripts\activate
pip install -r requirements-dev.txt
uvicorn app.main:app --reload --port 8000

# 前端
cd frontend
npm install
npm run dev
```

需要本地 PostgreSQL 16 + pgvector（向量列）与 Redis（队列/通知；缺省时降级为进程内模式）。

## 测试

```bash
cd backend && python -m pytest          # 单元 + API 测试
python -m pytest -m integration         # 需真实 LLM/Embedding
```

# 企业级 AI 知识库实施计划（知识图谱 + 团队协同双特色）

## Context

用户要构建一个**有差异化特色的企业级 AI 知识库**（不与 MaxKB/Dify/RAGFlow 同质化）。已确定：

- **两大特色**：
  1. **知识图谱可视化**：AI 自动抽取文档实体/关系（GraphRAG），交互式力导向图谱，点击节点跳转文档，问答结合向量检索 + 图邻居扩展
  2. **团队协作 + AI 双驱动**：多人实时协同编辑（Yjs CRDT），AI 自动摘要/标签/关联推荐
- **技术栈**：Vue3 + TS + Vite + Pinia + Element Plus + TipTap/Yjs + AntV G6 v5；FastAPI + SQLAlchemy 2.0 async + Alembic + Celery + Redis；PostgreSQL 16 + pgvector；Docker Compose 部署
- 工作目录 `c:\Users\15573\Desktop\知识库` 为空，全新项目

## 关键选型决策

| 决策点 | 结论 | 理由 |
|---|---|---|
| 图谱可视化 | AntV G6 v5 | 图分析场景；X6 是流程图编辑器，不匹配 |
| AI 封装 | 自封装轻量层（openai SDK ~200行 wrapper），不用 LangChain | 只有 embedding/chat/JSON抽取 三个调用；base_url 兼容 DeepSeek/Qwen/Ollama |
| 图数据存储 | 关系表 entities/edges + 递归 CTE，不用 Apache AGE | AGE 驱动与 asyncpg 不兼容；1-2 跳邻居查询索引表足够 |
| Yjs 服务端 | pycrdt + pycrdt-websocket | 原生 ASGI 可挂载 FastAPI，勿自实现 CRDT 协议 |
| Embedding | 独立配置，默认 1024 维 | **DeepSeek 无 embedding API**，LLM 与 Embedding 必须拆两套配置（如 LLM=DeepSeek + Embedding=Qwen/Ollama bge-m3） |
| 流式输出 | SSE（POST + fetch ReadableStream） | EventSource 仅支持 GET，前端封装 useSSE |
| 向量索引 | HNSW（m=16, ef_construction=64） | 无需训练，小数据集召回稳定 |

## 项目结构（monorepo）

```
知识库/
├── frontend/               # Vue3 + Vite + TS
│   ├── src/
│   │   ├── api/            # auth/spaces/documents/chat/graph 模块化请求
│   │   ├── stores/         # pinia
│   │   ├── views/          # auth/spaces/documents/chat/graph
│   │   ├── components/     # editor(TipTap)/graph(G6)/chat(引用卡片)
│   │   ├── composables/    # useSSE.ts, useCollab.ts
│   │   └── types/
│   ├── Dockerfile          # node build → nginx
│   └── nginx.conf          # /api 反代(SSE关缓冲) + /ws Upgrade
├── backend/
│   ├── app/
│   │   ├── main.py         # 挂载 routers + collab ASGI + /ws/notify
│   │   ├── core/           # config(pydantic-settings)/security(JWT)/deps/exceptions
│   │   ├── db/             # async engine/session
│   │   ├── models/         # user/space/document/chunk/graph/chat/collab/job
│   │   ├── schemas/        # pydantic DTO
│   │   ├── api/v1/         # auth/spaces/documents/search/chat/graph/comments/notifications/jobs
│   │   ├── services/       # llm.py/embedding.py/chunker.py/retrieval.py/extraction.py/rag.py/parsers/
│   │   ├── tasks/          # celery: parse/embed/extract/summarize/collab_flush
│   │   └── ws/             # collab.py(pycrdt-websocket)/notify.py
│   ├── alembic/versions/
│   ├── tests/              # unit/api/eval(qa样例集)
│   └── pyproject.toml
├── docker-compose.yml      # postgres(pgvector/pgvector:pg16)/redis/backend/worker/frontend
├── .env.example
├── Makefile                # up/migrate/test/seed
└── README.md
```

## 核心数据库设计

- **users / spaces / space_members**（role: owner/admin/member，UNIQUE(space_id,user_id)）
- **documents**：space_id, title, source_type(editor/upload), content_json(JSONB, TipTap), content_text(纯文本), status(uploaded/processing/ready/failed), summary, tags(JSONB)
- **document_versions**：UNIQUE(document_id, version_no)，手动保存/协同关闭/恢复均 bump
- **chunks**：document_id, space_id(反规范化过滤), seq, content, token_count, section_path, `embedding VECTOR(1024)` HNSW索引, content_hash(幂等)；UNIQUE(document_id,seq)
- **entities**：space_id, name, name_norm, type(person/organization/concept/technology/product/event/other), description, aliases(JSONB), mention_count；UNIQUE(space_id,name_norm,type)
- **entity_edges**：src_id/dst_id/relation/description/weight/evidence_chunk_ids(JSONB cap 20)；UNIQUE(space_id,src_id,dst_id,relation)
- **chunk_entities**：chunk_id×entity_id 中间表（GraphRAG 桥）
- **chat_sessions / chat_messages**：messages 含 citations(JSONB) 与 meta(JSONB 检索调试)
- **doc_collab_state**：document_id PK, yupdate BYTEA（Yjs 快照）
- **ai_jobs**：job_type(parse/embed/extract/summarize), status, celery_task_id
- **comments / notifications**

图扩展核心 SQL：递归 CTE 按 src_id=ANY(seeds) 扩 1-2 跳邻居。

## 核心 API

- REST `/api/v1`：auth(register/login/me)、spaces(CRUD+members)、documents(CRUD/upload multipart 20MB/versions/restore/related/jobs)、search(向量)、**chat/ask(SSE 流式)**、graph(overview/subgraph/document graph/entity detail)、comments、notifications
- WS：`/ws/collab/{doc_id}?token=`（y-websocket 协议）、`/ws/notify?token=`（job.completed/comment.created/doc.updated）
- SSE 事件协议：`citations` → `delta`* → `done`；检索>5s 发 `: keepalive` 心跳

## 分阶段实施（每阶段：pytest 绿 + 手动验证 + git commit）

### P0 脚手架
后端骨架(/healthz) + Vite 前端骨架 + docker-compose 四服务 + .env.example + Makefile
验证：`docker compose up` → curl healthz OK → 前端可访问

### P1 认证 + RBAC + 空间
Alembic 初始化，users/spaces/space_members；JWT + bcrypt；`require_space_role` 依赖；前端登录注册 + 路由守卫
验证：注册→登录→/me→401/403 测试全绿

### P2 文档管理与上传解析
documents/versions 模型；CRUD + 版本恢复；parsers(pymupdf/python-docx/md)；ai_jobs + parse 任务
验证：上传 pdf/docx/md 解析入库、版本可恢复

### P3 向量化 + 向量检索
chunks 迁移(VECTOR 1024 + HNSW)；EmbeddingClient；chunker(标题感知递归切分 512 token overlap 64, section_path)；Celery 编排 parse→chunk→embed→ready；`POST /search`；完成推 WS 通知
测试：fake embedding(确定性 hash 向量)；集成测试标记 integration
验证：上传→ready→search 命中

### P4 RAG 问答 + SSE + 引用（**MVP 核心里程碑**）
chat 模型；LLMClient(stream)；retrieval v1(纯向量)；rag.py(prompt: 按提问语言回答、[n] 引用、知识不足明确说明)；`POST /chat/ask` SSE；前端 ChatView 流式渲染 + 引用卡片跳转
验证：上传 2-3 篇相关文档→提问→流式回答带引用可跳转

### P5 图谱抽取 + 可视化
entities/edges/chunk_entities 迁移；extraction.py（见难点方案）；Celery extract 任务；graph 4 个查询 API；前端 G6 图谱页（力导向/类型着色/搜索过滤/节点抽屉跳文档）+ 文档"关联知识"卡片
验证：3 篇互引文档→抽取→图谱可见连接、节点跳转

### P6 GraphRAG 混合检索
retrieval v2：向量 top-20 → chunk_entities 映射实体 top5 → 递归 CTE 1-2 跳扩展 top15 → 反查关联 chunk → 去重 → 加权重排(score = 0.7×cosine + 0.3×graph_boost) → top8 上下文；无图命中退化为纯向量；meta 记录检索过程（前端可展开"检索过程"，差异化亮点）；qa_sample.json 评估 v1/v2
验证：GraphRAG 命中率 ≥ 纯向量，跨文档实体问题更优

### P7 实时协同 + 评论 + 通知
pycrdt-websocket 挂载 `/ws/collab`，ASGI 中间件握手 JWT+space 权限；持久化三层（房间启动加载/防抖 3s 落库/最后一人离开 flush→物化 content→版本快照→重嵌入→通知）；TipTap Collaboration + CollaborationCursor；评论 API + 面板
**写路径互斥**：协同房间活跃期间 REST 保存 content 返回 409（仅 title 可改），避免 CRDT 双写冲突
验证：双浏览器互见光标实时编辑，关闭后版本+1、搜索命中新内容

### P8 AI 双驱动 + 收尾
summarize 任务（摘要+标签写回+通知）；`GET /documents/{id}/related`（向量近邻 top5 排除自身）；AI 内容标注；nginx SSE/WS 配置确认；make seed 示例数据
验证：保存文档→通知→摘要/标签/推荐出现

依赖链：P0→P1→P2→P3→P4→P5→P6→P7→P8（P7 与 P5/P6 无依赖可对调）

## 关键技术方案

### 实体关系抽取（extraction.py）
- chunk 级抽取，附文档标题+section_path 上下文，skip <30 token
- System prompt 强约束：仅用文中信息禁推测、type 枚举、evidence_quote 逐字摘录 ≤200 字、空返回空数组、只输出 JSON
- temperature=0 + JSON mode → strip 围栏 json.loads → Pydantic 校验 → 失败一次修复重试 → 再失败标记 extract_failed 不阻塞
- 关系引用实体不存在则丢弃（阻断幻觉关联）
- 去重合并：normalize(lower/去标点) → name_norm 或 aliases 匹配合并（aliases∪、mention_count+1、description 取长）→ 关系 upsert weight+1
- 幂等：chunk content_hash 跳过已抽取

### GraphRAG 检索（retrieval.py）
向量 top20 → 实体映射 top5 → 图扩展 top15 → 反查 chunk → score=0.7×cosine+0.3×graph_boost → top8；不引入外部 reranker（预留 RERANK_ENABLED）；过程写 meta

### Yjs 协同服务端（ws/collab.py）
`app.mount("/ws/collab", YWebsocket(...))`；ASGI 中间件鉴权；房间启动从 doc_collab_state 或 content_json 初始化；更新防抖 3s；离开 flush→Celery 物化；单进程起步，瓶颈时拆独立容器

### SSE（api/v1/chat.py）
async generator：先检索发 citations 事件，再 LLM stream 逐 token delta，落库后 done；捕获 CancelledError 取消上游并落库已生成部分；nginx `proxy_buffering off`

## docker-compose 要点

- `pgvector/pgvector:pg16` 镜像免自编译；healthcheck pg_isready / redis-cli ping
- backend 与 worker 同镜像只差命令（schema 一致）
- `CREATE EXTENSION vector` 放 Alembic 迁移（幂等）
- .env 必含：LLM_BASE_URL/LLM_API_KEY/LLM_MODEL/EMBEDDING_BASE_URL/EMBEDDING_API_KEY/EMBEDDING_MODEL/EMBEDDING_DIM=1024/DATABASE_URL/REDIS_URL/JWT_SECRET
- 迁移：`make migrate`（exec alembic upgrade head）

## 验证方案

- pytest：真 PG（pgvector 需要真实扩展，不用 SQLite）；conftest 提供 FakeLLMClient/FakeEmbeddingClient 注入 app.state；unit（chunker/抽取修复/合并/打分纯函数）+ api（httpx ASGITransport 全栈：RBAC 403、SSE 事件序列、上传解析）；`@pytest.mark.integration` 真实 LLM 手动跑
- 两条核心手动路径：
  1. P4：注册→建空间→上传 3 篇 md→ready→提问→流式回答带 [n] 引用→点击跳转
  2. P7：双浏览器协同→互见光标→关闭→版本+1→搜索命中→他人收通知
- 每阶段 git commit（符合用户工作流要求：每次变更配套 commit + 测试通过后交付）

# KB-Graph — Enterprise AI Knowledge Base

A next-generation enterprise knowledge management platform powered by **GraphRAG knowledge graph visualization** and **team collaboration + AI dual-engine**.

## Key Features

### 1. Knowledge Graph Visualization (GraphRAG)
- AI auto-extracts entities and relationships from documents, building an interactive force-directed graph (AntV G6 v5)
- Click graph nodes to navigate to related documents, linking graph exploration with Q&A
- Hybrid retrieval: vector similarity + graph neighbor expansion for superior cross-document answers

### 2. Team Collaboration + AI Dual-Engine
- Yjs CRDT-based real-time collaborative editing with shared cursors
- Comments and notification system
- AI auto-generates summaries, tags, and related document recommendations upon upload

### 3. More
- Full-text + vector (pgvector/HNSW) hybrid search
- Streaming AI Q&A (SSE) with source citations
- Role-based access control per space (owner / admin / member)
- Multi-format document parsing: PDF, DOCX, Markdown, TXT

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | Vue 3 + TypeScript + Vite + Pinia + Element Plus + TipTap/Yjs + AntV G6 v5 |
| Backend | Python FastAPI + SQLAlchemy 2.0 (async) + Celery + Redis |
| Database | PostgreSQL 16 + pgvector (HNSW index) |
| AI | OpenAI-compatible API (DeepSeek / Qwen / Ollama), independent LLM & Embedding config |
| Deployment | Docker Compose (one-command startup) |

## Project Structure

```
├── frontend/                # Vue 3 + Vite SPA
│   ├── src/
│   │   ├── api/             # HTTP client modules
│   │   ├── components/      # Shared components (graph, notifications, empty state, etc.)
│   │   ├── layouts/         # Page layouts
│   │   ├── router/          # Vue Router config
│   │   ├── stores/          # Pinia state management
│   │   ├── styles/          # Global styles (CSS variables, reset, transitions)
│   │   ├── views/           # Page components (login, spaces, documents, graph, AI chat)
│   │   └── __tests__/       # Frontend tests (Vitest)
│   ├── Dockerfile
│   └── nginx.conf
├── backend/
│   ├── app/
│   │   ├── api/v1/          # REST API endpoints (auth, spaces, documents, graph, chat, search, comments, etc.)
│   │   ├── core/            # Config, security, dependency injection
│   │   ├── db/              # Database session management
│   │   ├── models/          # SQLAlchemy ORM models
│   │   ├── schemas/         # Pydantic validation schemas
│   │   ├── services/        # Business logic (LLM, Embedding, RAG, entity extraction, parsing, chunking)
│   │   ├── tasks/           # Celery async tasks (vectorization, graph extraction, summarization)
│   │   └── ws/              # WebSocket (collaborative editing)
│   ├── tests/               # Backend tests (pytest)
│   ├── alembic/             # Database migrations
│   └── Dockerfile
├── docker-compose.yml       # Full-stack orchestration
├── Makefile                 # Common commands
├── .env.example             # Environment variable template
└── .gitattributes           # Line ending normalization
```

## Quick Start (Docker)

```bash
git clone <repo-url> && cd kb-graph
cp .env.example .env          # Edit .env with your LLM / Embedding API keys
docker compose up -d --build
docker compose exec backend alembic upgrade head
# Frontend: http://localhost
# Backend API docs: http://localhost:8000/docs
```

## Local Development

**Prerequisites:** PostgreSQL 16 + pgvector extension, Redis (optional, falls back to in-process mode), Python 3.13+, Node.js 20+

### Backend

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # macOS / Linux
pip install -r requirements-dev.txt
cp ../.env.example .env         # Configure your API keys
uvicorn app.main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev                     # http://localhost:5173
```

### Common Commands

```bash
make up          # Start Docker Compose
make down        # Stop Docker Compose
make migrate     # Run database migrations
make test        # Run backend tests
make seed        # Create demo data
```

## Testing

```bash
# Backend
cd backend && python -m pytest                  # Unit + API tests
python -m pytest -m integration                 # Integration tests (requires real LLM/Embedding)

# Frontend
cd frontend && npm test                         # Vitest unit tests
```

## API Documentation

Once the backend is running, visit:

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Environment Variables

See `.env.example` for all variables. Key configuration:

| Variable | Description |
|----------|-------------|
| `LLM_BASE_URL` | LLM API endpoint (DeepSeek / Qwen / Ollama) |
| `LLM_API_KEY` | LLM API key |
| `LLM_MODEL` | Model name (defaults to `deepseek-chat`) |
| `EMBEDDING_BASE_URL` | Embedding API endpoint (leave empty for hash-based fallback, dev/test only) |
| `EMBEDDING_MODEL` | Embedding model (defaults to `bge-m3`) |
| `DATABASE_URL` | PostgreSQL connection string |
| `REDIS_URL` | Redis connection string |

## License

MIT
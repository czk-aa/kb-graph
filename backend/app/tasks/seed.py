"""种子数据脚本，用于演示和测试。

用法: python -m app.tasks.seed
"""
import asyncio
import sys


SAMPLE_DOCS = [
    {
        "title": "FastAPI 微服务架构设计",
        "content": """# FastAPI 微服务架构设计

## 概述
FastAPI 是一个现代、高性能的 Python Web 框架，基于 Starlette 和 Pydantic，
特别适合构建微服务架构。

## 核心组件
- **路由层**：使用 APIRouter 组织 API 端点，支持依赖注入
- **中间件**：CORS、认证、请求日志等
- **数据库**：通过 SQLAlchemy 异步操作 PostgreSQL
- **缓存**：使用 Redis 缓存热点数据，减少数据库压力
- **任务队列**：Celery 处理异步任务，如发送邮件、生成报告

## 性能优化
- 使用 async/await 异步非阻塞 I/O
- 数据库连接池管理
- Redis 缓存策略：Cache-Aside 模式
- Nginx 反向代理 + 负载均衡

## 部署方案
- Docker Compose 一体化部署
- Kubernetes 集群部署
- CI/CD 使用 GitHub Actions
""",
    },
    {
        "title": "PostgreSQL 向量检索实战",
        "content": """# PostgreSQL 向量检索实战

## pgvector 扩展
PostgreSQL 的 pgvector 扩展提供了高效的向量存储和检索能力。

## 核心概念
- **向量维度**：OpenAI text-embedding-3-small 输出 1536 维向量
- **索引类型**：HNSW（层次导航小世界）索引，适合高维向量
- **距离度量**：余弦相似度（cosine distance）最常用

## HNSW 索引
HNSW 是一种基于图的近似最近邻搜索算法：
- 构建多层图结构，每层节点数递减
- 上层用于长距离跳转，下层用于精确搜索
- 参数 m=16, ef_construction=64 推荐配置

## 查询优化
```sql
SELECT * FROM chunks
ORDER BY embedding <=> query_vector
LIMIT 10;
```
- `<=>` 运算符计算余弦距离
- 结合 HNSW 索引，10万向量检索 < 10ms

## 与 Elasticsearch 对比
- pgvector 优势：数据一致性、事务支持、无需额外服务
- Elasticsearch 优势：全文检索、聚合分析、更大规模
- 推荐：小中型项目用 pgvector，大型项目两者结合
""",
    },
    {
        "title": "GraphRAG 知识图谱增强检索",
        "content": """# GraphRAG 知识图谱增强检索

## 什么是 GraphRAG
GraphRAG 是结合知识图谱和向量检索的混合检索技术，
通过实体关系图增强 RAG 的召回质量。

## 工作流程
1. **文档解析**：将文档分块，提取关键实体和关系
2. **向量召回**：使用向量相似度召回 top-k 相关 chunk
3. **图扩展**：从命中的 chunk 提取实体，沿关系图扩展 1-2 跳
4. **候选扩充**：反查邻居实体关联的 chunk，加入候选池
5. **加权重排**：score = 0.7 × 向量相似度 + 0.3 × 图增强分数

## 实体类型
- 技术（Technology）：FastAPI、PostgreSQL、Redis
- 概念（Concept）：微服务、向量检索、RAG
- 人物（Person）：项目成员
- 组织（Organization）：公司、团队
- 产品（Product）：软件产品

## 优势
- 跨文档关联：通过实体图发现不同文档间的隐含关系
- 知识补全：图扩展能召回向量检索遗漏的相关信息
- 可解释性：可视化的关系图让用户理解检索逻辑
""",
    },
    {
        "title": "Redis 缓存策略与最佳实践",
        "content": """# Redis 缓存策略与最佳实践

## 缓存模式
- **Cache-Aside**：应用先查缓存，未命中则查数据库并回写缓存
- **Read-Through**：缓存层自动处理数据库读取
- **Write-Through**：写入时同步更新缓存和数据库
- **Write-Behind**：异步批量写入数据库

## Redis 数据结构
- String：缓存简单键值对
- Hash：缓存对象属性
- List：消息队列、时间线
- Set：标签、去重集合
- Sorted Set：排行榜、优先级队列

## 缓存失效策略
- TTL 过期时间
- LRU/LFU 淘汰策略
- 主动失效：数据变更时删除相关缓存

## 与 PostgreSQL 配合
- 热点数据缓存到 Redis，减少数据库查询
- 使用 Redis Pub/Sub 实现跨服务消息通知
- Celery 任务队列基于 Redis 实现
""",
    },
    {
        "title": "Docker 容器化部署指南",
        "content": """# Docker 容器化部署指南

## Docker Compose 编排
使用 docker-compose.yml 定义多服务应用：
- PostgreSQL 16 + pgvector
- Redis 7
- FastAPI 后端
- Celery Worker
- Nginx 前端

## 多阶段构建
- 后端：pip install → slim 镜像 → 复制依赖
- 前端：npm build → nginx 镜像 → 复制静态文件

## 数据持久化
- PostgreSQL 数据卷：pgdata
- Redis 数据卷：redisdata
- 文件上传卷：uploads

## 健康检查
- PostgreSQL：pg_isready
- Redis：redis-cli ping
- 后端：/healthz 端点

## 生产环境建议
- 使用 secrets 管理敏感信息
- 配置资源限制（CPU/内存）
- 日志收集到 ELK
- 监控使用 Prometheus + Grafana
""",
    },
]


async def _seed() -> None:
    from app.db.session import get_session_factory
    from app.models import User, Space, SpaceMember, SpaceRole, Document
    from app.tasks.extract_task import enqueue_extract
    from app.tasks.summarize_task import enqueue_summarize

    factory = get_session_factory()
    async with factory() as db:
        # 创建演示用户
        from app.core.security import hash_password

        existing = await db.scalar(
            __import__("sqlalchemy").select(User).where(User.email == "demo@kb-graph.com")
        )
        if existing:
            print("[seed] 种子数据已存在，跳过")
            return

        demo_user = User(
            email="demo@kb-graph.com",
            password_hash=hash_password("demo123"),
            nickname="Demo",
        )
        db.add(demo_user)
        await db.flush()

        # 创建演示空间
        space = Space(name="技术知识库", description="AI 驱动的企业技术知识库", owner_id=demo_user.id)
        db.add(space)
        await db.flush()

        db.add(SpaceMember(space_id=space.id, user_id=demo_user.id, role=SpaceRole.owner))
        await db.flush()

        # 创建示例文档
        for i, doc_data in enumerate(SAMPLE_DOCS):
            doc = Document(
                space_id=space.id,
                title=doc_data["title"],
                content_text=doc_data["content"],
                source_type="editor",
                status="ready",
                created_by=demo_user.id,
            )
            db.add(doc)
            await db.flush()

            # 触发图谱抽取 + AI摘要（embedding 需单独配置 API Key）
            await enqueue_extract(doc.id)
            await enqueue_summarize(doc.id)

            print(f"[seed] 已创建文档: {doc_data['title']}")

        await db.commit()

    print("\n[seed] 种子数据创建完成！")
    print("  登录邮箱: demo@kb-graph.com")
    print("  密码: demo123")
    print(f"  共 {len(SAMPLE_DOCS)} 篇技术文档")
    print("  向量化 + 图谱抽取已触发")
    print("  等待任务完成后即可体验完整功能")


def main() -> None:
    asyncio.run(_seed())


if __name__ == "__main__":
    main()
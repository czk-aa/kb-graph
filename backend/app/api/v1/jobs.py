"""异步任务状态查询。"""
from fastapi import APIRouter

from app.core.deps import CurrentUser, DbSession, require_space_role
from app.core.exceptions import NotFoundError
from app.models.job import AiJob
from app.schemas.document import JobOut

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.get("/{job_id}", response_model=JobOut)
async def get_job(job_id: int, current_user: CurrentUser, db: DbSession) -> JobOut:
    job = await db.get(AiJob, job_id)
    if job is None:
        raise NotFoundError("任务不存在")
    await require_space_role("member")(job.space_id, current_user, db)
    return JobOut.model_validate(job)

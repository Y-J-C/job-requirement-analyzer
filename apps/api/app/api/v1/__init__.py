from fastapi import APIRouter

from app.api.v1.analysis import router as analysis_router
from app.api.v1.jobs import jobs_router, target_role_jobs_router
from app.api.v1.requirements import job_requirements_router, requirements_router
from app.api.v1.summary import router as summary_router
from app.api.v1.target_roles import router as target_roles_router

router = APIRouter()
router.include_router(target_roles_router)
router.include_router(analysis_router)
router.include_router(target_role_jobs_router)
router.include_router(jobs_router)
router.include_router(job_requirements_router)
router.include_router(requirements_router)
router.include_router(summary_router)

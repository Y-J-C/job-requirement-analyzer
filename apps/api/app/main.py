from typing import Literal

from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy.exc import SQLAlchemyError

from app.api.v1 import router as api_v1_router
from app.core.config import get_settings
from app.core.database import check_database_connection


class HealthResponse(BaseModel):
    status: Literal["ok"]


class ReadinessResponse(BaseModel):
    status: Literal["ready"]
    database: Literal["ok"]


def create_app() -> FastAPI:
    settings = get_settings()
    application = FastAPI(
        title="岗位门槛分析系统 API",
        version="0.1.0",
    )
    application.add_middleware(
        CORSMiddleware,
        allow_origins=[settings.web_origin],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    application.include_router(api_v1_router, prefix="/api/v1")

    @application.get("/health", response_model=HealthResponse, tags=["health"])
    async def health() -> HealthResponse:
        return HealthResponse(status="ok")

    @application.get("/health/ready", response_model=ReadinessResponse, tags=["health"])
    def readiness() -> ReadinessResponse:
        try:
            check_database_connection()
        except SQLAlchemyError as error:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Database is unavailable",
            ) from error

        return ReadinessResponse(status="ready", database="ok")

    return application


app = create_app()

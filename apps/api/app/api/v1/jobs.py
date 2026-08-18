import uuid
from typing import Annotated

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    Response,
    UploadFile,
    status,
)
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.ai.contracts import RequirementAnalyzer
from app.ai.dependencies import get_requirement_analyzer
from app.core.config import Settings, get_settings
from app.core.database import get_session
from app.parsing.errors import DocumentError
from app.parsing.validation import IMAGE_MEDIA_TYPES, validate_image_batch, validate_upload
from app.schemas.analysis import AnalysisRunResponse
from app.schemas.job_intake import (
    JobIntakeMetadata,
    JobIntakeResponse,
    JobSourceType,
)
from app.schemas.job_posting import (
    JobPostingCreate,
    JobPostingListResponse,
    JobPostingMetadataUpdate,
    JobPostingResponse,
)
from app.schemas.source_file import (
    JobPostingUploadMetadata,
    JobPostingUploadResponse,
    SourceFileResponse,
)
from app.services.analysis import create_ai_analysis_run, get_latest_analysis_run
from app.services.job_intake import create_file_intake, create_text_intake
from app.services.job_posting import (
    create_job_posting,
    delete_job_posting,
    list_job_postings,
    retry_failed_job,
    update_job_metadata,
)
from app.services.resource_lookup import get_job
from app.services.source_file import create_uploaded_job, get_source_file
from app.services.target_role import get_target_role
from app.storage.contracts import ObjectStore, StorageUnavailableError
from app.storage.dependencies import get_object_store

target_role_jobs_router = APIRouter(prefix="/target-roles", tags=["jobs"])
jobs_router = APIRouter(prefix="/jobs", tags=["jobs"])
SessionDependency = Annotated[Session, Depends(get_session)]
SettingsDependency = Annotated[Settings, Depends(get_settings)]
AnalyzerDependency = Annotated[RequirementAnalyzer, Depends(get_requirement_analyzer)]
ObjectStoreDependency = Annotated[ObjectStore, Depends(get_object_store)]


def require_target_role(
    session: Session,
    role_id: uuid.UUID,
) -> None:
    if get_target_role(session, role_id) is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Target role not found",
        )


@target_role_jobs_router.post(
    "/{role_id}/jobs",
    response_model=JobPostingResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_job_posting_endpoint(
    role_id: uuid.UUID,
    payload: JobPostingCreate,
    session: SessionDependency,
) -> JobPostingResponse:
    require_target_role(session, role_id)
    return JobPostingResponse.model_validate(create_job_posting(session, role_id, payload))


@target_role_jobs_router.post(
    "/{role_id}/jobs/upload",
    response_model=JobPostingUploadResponse,
    status_code=status.HTTP_201_CREATED,
)
def upload_job_posting_endpoint(
    role_id: uuid.UUID,
    session: SessionDependency,
    settings: SettingsDependency,
    store: ObjectStoreDependency,
    company_name: Annotated[str, Form()],
    job_title: Annotated[str, Form()],
    recruitment_stage: Annotated[str, Form()],
    file: Annotated[UploadFile, File()],
    city: Annotated[str | None, Form()] = None,
    source_url: Annotated[str | None, Form()] = None,
) -> JobPostingUploadResponse:
    require_target_role(session, role_id)
    try:
        metadata = JobPostingUploadMetadata(
            company_name=company_name,
            job_title=job_title,
            recruitment_stage=recruitment_stage,
            city=city or None,
            source_url=source_url or None,
        )
    except ValidationError as error:
        raise HTTPException(status_code=422, detail="Invalid job metadata") from error
    try:
        upload = validate_upload(
            file.file,
            file.filename or "",
            file.content_type,
            max_bytes=settings.upload_max_bytes,
        )
        job, source_file = create_uploaded_job(
            session,
            store,
            target_role_id=role_id,
            metadata=metadata,
            upload=upload,
            max_attempts=settings.document_worker_max_attempts,
        )
    except DocumentError as error:
        raise HTTPException(
            status_code=422,
            detail={"code": error.code, "message": str(error)},
        ) from error
    except StorageUnavailableError as error:
        raise HTTPException(status_code=503, detail="File storage is unavailable") from error
    finally:
        if "upload" in locals():
            upload.content.close()
    return JobPostingUploadResponse(
        job=JobPostingResponse.model_validate(job),
        source_file=SourceFileResponse.model_validate(source_file),
    )


@target_role_jobs_router.post(
    "/{role_id}/jobs/intake",
    response_model=JobIntakeResponse,
    status_code=status.HTTP_201_CREATED,
)
def intake_job_posting_endpoint(
    role_id: uuid.UUID,
    session: SessionDependency,
    settings: SettingsDependency,
    analyzer: AnalyzerDependency,
    store: ObjectStoreDependency,
    source_type: Annotated[JobSourceType, Form()],
    recruitment_stage: Annotated[str, Form()],
    text: Annotated[str | None, Form()] = None,
    company_name: Annotated[str | None, Form()] = None,
    job_title: Annotated[str | None, Form()] = None,
    city: Annotated[str | None, Form()] = None,
    source_url: Annotated[str | None, Form()] = None,
    files: Annotated[list[UploadFile] | None, File()] = None,
) -> JobIntakeResponse:
    require_target_role(session, role_id)
    try:
        metadata = JobIntakeMetadata(
            company_name=company_name or None,
            job_title=job_title or None,
            recruitment_stage=recruitment_stage,
            city=city or None,
            source_url=source_url or None,
        )
    except ValidationError as error:
        raise HTTPException(status_code=422, detail="Invalid job metadata") from error

    submitted_files = files or []
    normalized_text = (text or "").strip()
    if source_type == JobSourceType.TEXT:
        if submitted_files or not normalized_text:
            raise HTTPException(status_code=422, detail="Text intake requires text only")
        if len(normalized_text) > settings.extracted_text_max_chars:
            raise HTTPException(status_code=422, detail="Job text exceeds the safe limit")
        job, run = create_text_intake(
            session,
            target_role_id=role_id,
            metadata=metadata,
            text=normalized_text,
            model_provider=analyzer.provider_name,
            model_name=analyzer.model_name,
            analysis_max_attempts=settings.analysis_worker_max_attempts,
        )
        return JobIntakeResponse(
            job=JobPostingResponse.model_validate(job),
            source_files=[],
            analysis_run=AnalysisRunResponse.model_validate(run) if run else None,
        )
    if normalized_text:
        raise HTTPException(status_code=422, detail="File intake cannot include text")
    if source_type == JobSourceType.DOCUMENT and len(submitted_files) != 1:
        raise HTTPException(status_code=422, detail="Document intake requires one file")

    uploads = []
    try:
        for submitted_file in submitted_files:
            uploads.append(
                validate_upload(
                    submitted_file.file,
                    submitted_file.filename or "",
                    submitted_file.content_type,
                    max_bytes=settings.upload_max_bytes,
                    max_image_pixels=settings.image_max_pixels,
                )
            )
        if source_type == JobSourceType.DOCUMENT:
            if uploads[0].detected_media_type in IMAGE_MEDIA_TYPES:
                raise DocumentError("unsupported_file_type", "Document intake requires a document")
        else:
            validate_image_batch(
                uploads,
                max_files=settings.image_max_files,
                max_total_bytes=settings.image_total_max_bytes,
                max_total_pixels=settings.image_total_max_pixels,
            )
        job, sources = create_file_intake(
            session,
            store,
            target_role_id=role_id,
            metadata=metadata,
            uploads=uploads,
            max_attempts=settings.document_worker_max_attempts,
        )
    except DocumentError as error:
        raise HTTPException(
            status_code=422,
            detail={"code": error.code, "message": str(error)},
        ) from error
    except StorageUnavailableError as error:
        raise HTTPException(status_code=503, detail="File storage is unavailable") from error
    finally:
        for upload in uploads:
            upload.content.close()
    return JobIntakeResponse(
        job=JobPostingResponse.model_validate(job),
        source_files=[SourceFileResponse.model_validate(source) for source in sources],
        analysis_run=None,
    )


@target_role_jobs_router.get("/{role_id}/jobs", response_model=JobPostingListResponse)
def list_job_postings_endpoint(
    role_id: uuid.UUID,
    session: SessionDependency,
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
) -> JobPostingListResponse:
    require_target_role(session, role_id)
    items, total = list_job_postings(session, role_id, offset=offset, limit=limit)
    return JobPostingListResponse(items=items, total=total)


@jobs_router.get("/{job_id}", response_model=JobPostingResponse)
def get_job_posting_endpoint(
    job_id: uuid.UUID,
    session: SessionDependency,
) -> JobPostingResponse:
    job_posting = get_job(session, job_id)
    if job_posting is None:
        raise HTTPException(status_code=404, detail="Job posting not found")
    return JobPostingResponse.model_validate(job_posting)


@jobs_router.patch("/{job_id}", response_model=JobPostingResponse)
def update_job_posting_endpoint(
    job_id: uuid.UUID,
    payload: JobPostingMetadataUpdate,
    session: SessionDependency,
) -> JobPostingResponse:
    job_posting = get_job(session, job_id)
    if job_posting is None:
        raise HTTPException(status_code=404, detail="Job posting not found")
    return JobPostingResponse.model_validate(
        update_job_metadata(session, job_posting, payload)
    )


@jobs_router.post(
    "/{job_id}/retry",
    response_model=JobIntakeResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
def retry_job_posting_endpoint(
    job_id: uuid.UUID,
    session: SessionDependency,
    settings: SettingsDependency,
    analyzer: AnalyzerDependency,
) -> JobIntakeResponse:
    if get_job(session, job_id) is None:
        raise HTTPException(status_code=404, detail="Job posting not found")
    result = retry_failed_job(
        session,
        job_id=job_id,
        model_provider=analyzer.provider_name,
        model_name=analyzer.model_name,
        analysis_max_attempts=settings.analysis_worker_max_attempts,
    )
    if result is None:
        raise HTTPException(status_code=409, detail="Job cannot be retried in its current state")
    job, sources, run = result
    return JobIntakeResponse(
        job=JobPostingResponse.model_validate(job),
        source_files=[SourceFileResponse.model_validate(source) for source in sources],
        analysis_run=AnalysisRunResponse.model_validate(run) if run else None,
    )


@jobs_router.get("/{job_id}/source-file", response_model=SourceFileResponse)
def get_source_file_endpoint(
    job_id: uuid.UUID,
    session: SessionDependency,
) -> SourceFileResponse:
    if get_job(session, job_id) is None:
        raise HTTPException(status_code=404, detail="Job posting not found")
    source_file = get_source_file(session, job_id)
    if source_file is None:
        raise HTTPException(status_code=404, detail="Source file not found")
    return SourceFileResponse.model_validate(source_file)


@jobs_router.post(
    "/{job_id}/analyze",
    response_model=AnalysisRunResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
def analyze_job_posting_endpoint(
    job_id: uuid.UUID,
    session: SessionDependency,
    settings: SettingsDependency,
    analyzer: AnalyzerDependency,
) -> AnalysisRunResponse:
    job_posting = get_job(session, job_id)
    if job_posting is None:
        raise HTTPException(status_code=404, detail="Job posting not found")
    analysis_run = create_ai_analysis_run(
        session,
        job_posting,
        model_provider=analyzer.provider_name,
        model_name=analyzer.model_name,
        max_attempts=settings.analysis_worker_max_attempts,
    )
    if analysis_run is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Job is already being analyzed or has review data",
        )
    return AnalysisRunResponse.model_validate(analysis_run)


@jobs_router.get(
    "/{job_id}/analysis-runs/latest",
    response_model=AnalysisRunResponse,
)
def get_latest_analysis_run_endpoint(
    job_id: uuid.UUID,
    session: SessionDependency,
) -> AnalysisRunResponse:
    if get_job(session, job_id) is None:
        raise HTTPException(status_code=404, detail="Job posting not found")
    analysis_run = get_latest_analysis_run(session, job_id)
    if analysis_run is None:
        raise HTTPException(status_code=404, detail="Analysis run not found")
    return AnalysisRunResponse.model_validate(analysis_run)


@jobs_router.delete("/{job_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_job_posting_endpoint(
    job_id: uuid.UUID,
    session: SessionDependency,
    store: ObjectStoreDependency,
) -> Response:
    job_posting = get_job(session, job_id)
    if job_posting is None:
        raise HTTPException(status_code=404, detail="Job posting not found")
    try:
        delete_job_posting(session, job_posting, store=store)
    except StorageUnavailableError as error:
        raise HTTPException(status_code=503, detail="File storage is unavailable") from error
    return Response(status_code=status.HTTP_204_NO_CONTENT)

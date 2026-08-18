import logging
import uuid

from sqlalchemy.orm import Session

from app.models.job_posting import JobPosting, JobPostingStatus
from app.models.source_file import SourceFile
from app.parsing.validation import ValidatedUpload
from app.schemas.job_intake import JobIntakeMetadata
from app.services.analysis import enqueue_ai_analysis_run_locked
from app.storage.contracts import ObjectStore, StorageUnavailableError

logger = logging.getLogger(__name__)


def create_text_intake(
    session: Session,
    *,
    target_role_id: uuid.UUID,
    metadata: JobIntakeMetadata,
    text: str,
    model_provider: str,
    model_name: str,
    analysis_max_attempts: int,
):
    job = JobPosting(
        target_role_id=target_role_id,
        company_name=metadata.company_name,
        job_title=metadata.job_title,
        recruitment_stage=metadata.recruitment_stage,
        city=metadata.city,
        source_url=str(metadata.source_url) if metadata.source_url else None,
        original_text=text,
        status=JobPostingStatus.DRAFT,
    )
    session.add(job)
    session.flush()
    run = enqueue_ai_analysis_run_locked(
        session,
        job,
        model_provider=model_provider,
        model_name=model_name,
        max_attempts=analysis_max_attempts,
    )
    session.commit()
    session.refresh(job)
    if run is not None:
        session.refresh(run)
    return job, run


def create_file_intake(
    session: Session,
    store: ObjectStore,
    *,
    target_role_id: uuid.UUID,
    metadata: JobIntakeMetadata,
    uploads: list[ValidatedUpload],
    max_attempts: int,
) -> tuple[JobPosting, list[SourceFile]]:
    stored_keys: list[str] = []
    try:
        store.ensure_bucket()
        for upload in uploads:
            object_key = f"source-files/{uuid.uuid4().hex}"
            upload.content.seek(0)
            store.put(object_key, upload.content, upload.detected_media_type)
            stored_keys.append(object_key)

        job = JobPosting(
            target_role_id=target_role_id,
            company_name=metadata.company_name,
            job_title=metadata.job_title,
            recruitment_stage=metadata.recruitment_stage,
            city=metadata.city,
            source_url=str(metadata.source_url) if metadata.source_url else None,
            original_text="",
            status=JobPostingStatus.EXTRACTING,
        )
        session.add(job)
        session.flush()
        sources = [
            SourceFile(
                job_posting_id=job.id,
                sequence_index=index,
                object_key=object_key,
                original_filename=upload.original_filename,
                declared_mime_type=upload.declared_mime_type,
                detected_media_type=upload.detected_media_type,
                size_bytes=upload.size_bytes,
                sha256=upload.sha256,
                max_attempts=max_attempts,
            )
            for index, (upload, object_key) in enumerate(zip(uploads, stored_keys, strict=True))
        ]
        session.add_all(sources)
        session.commit()
        session.refresh(job)
        for source in sources:
            session.refresh(source)
        return job, sources
    except Exception:
        session.rollback()
        for object_key in stored_keys:
            try:
                store.delete(object_key)
            except StorageUnavailableError:
                logger.error("Could not remove object after intake failure")
        raise

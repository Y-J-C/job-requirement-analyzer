import logging
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.job_posting import JobPosting, JobPostingStatus
from app.models.source_file import SourceFile, SourceFileStatus
from app.parsing.contracts import ImageOcr
from app.parsing.errors import DocumentError
from app.parsing.parsers import parse_document
from app.parsing.validation import IMAGE_MEDIA_TYPES, ValidatedUpload
from app.schemas.source_file import JobPostingUploadMetadata
from app.security.malware import FileScanner, MalwareDetectedError
from app.services.analysis import enqueue_ai_analysis_run_locked
from app.storage.contracts import ObjectStore, StorageUnavailableError

logger = logging.getLogger(__name__)
PARSER_VERSION = "document-parser-v1"
IMAGE_OCR_VERSION = "image-ocr-v1"
SOURCE_TEXT_SEPARATOR = "\n\n"


@dataclass(frozen=True)
class ClaimedSourceFile:
    source_file_id: uuid.UUID
    object_key: str
    detected_media_type: str


def create_uploaded_job(
    session: Session,
    store: ObjectStore,
    *,
    target_role_id: uuid.UUID,
    metadata: JobPostingUploadMetadata,
    upload: ValidatedUpload,
    max_attempts: int,
) -> tuple[JobPosting, SourceFile]:
    object_key = f"source-files/{uuid.uuid4().hex}"
    store.ensure_bucket()
    upload.content.seek(0)
    store.put(object_key, upload.content, upload.detected_media_type)
    try:
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
        source_file = SourceFile(
            job_posting_id=job.id,
            object_key=object_key,
            original_filename=upload.original_filename,
            declared_mime_type=upload.declared_mime_type,
            detected_media_type=upload.detected_media_type,
            size_bytes=upload.size_bytes,
            sha256=upload.sha256,
            max_attempts=max_attempts,
        )
        session.add(source_file)
        session.commit()
        session.refresh(job)
        session.refresh(source_file)
        return job, source_file
    except Exception:
        session.rollback()
        try:
            store.delete(object_key)
        except StorageUnavailableError:
            logger.error("Could not remove object after database upload failure")
        raise


def get_source_file(session: Session, job_id: uuid.UUID) -> SourceFile | None:
    return session.scalar(
        select(SourceFile)
        .where(SourceFile.job_posting_id == job_id)
        .order_by(SourceFile.sequence_index.asc())
        .limit(1)
    )


def recover_stale_source_files(session: Session, *, now: datetime) -> int:
    stale_files = list(
        session.scalars(
            select(SourceFile)
            .where(
                SourceFile.parse_status == SourceFileStatus.RUNNING,
                SourceFile.lease_expires_at <= now,
            )
            .with_for_update(skip_locked=True)
        )
    )
    for source_file in stale_files:
        job = session.get(JobPosting, source_file.job_posting_id)
        source_file.worker_id = None
        source_file.lease_expires_at = None
        source_file.error_code = "worker_lease_expired"
        if source_file.attempt_count >= source_file.max_attempts:
            source_file.parse_status = SourceFileStatus.FAILED
            source_file.completed_at = now
            if job is not None:
                job.status = JobPostingStatus.FAILED
        else:
            source_file.parse_status = SourceFileStatus.PENDING
            source_file.available_at = now
            if job is not None:
                job.status = JobPostingStatus.EXTRACTING
    if stale_files:
        session.commit()
    return len(stale_files)


def claim_next_source_file(
    session: Session,
    *,
    worker_id: str,
    now: datetime,
    lease_seconds: int,
) -> ClaimedSourceFile | None:
    recover_stale_source_files(session, now=now)
    source_file = session.scalar(
        select(SourceFile)
        .where(
            SourceFile.parse_status == SourceFileStatus.PENDING,
            SourceFile.available_at <= now,
        )
        .order_by(SourceFile.available_at.asc(), SourceFile.created_at.asc())
        .with_for_update(skip_locked=True)
        .limit(1)
    )
    if source_file is None:
        return None
    job = session.get(JobPosting, source_file.job_posting_id)
    if job is None:
        source_file.parse_status = SourceFileStatus.FAILED
        source_file.error_code = "job_not_found"
        source_file.completed_at = now
        session.commit()
        return None
    source_file.parse_status = SourceFileStatus.RUNNING
    source_file.attempt_count += 1
    source_file.started_at = source_file.started_at or now
    source_file.lease_expires_at = now + timedelta(seconds=lease_seconds)
    source_file.worker_id = worker_id[:100]
    job.status = JobPostingStatus.EXTRACTING
    claimed = ClaimedSourceFile(
        source_file_id=source_file.id,
        object_key=source_file.object_key,
        detected_media_type=source_file.detected_media_type,
    )
    session.commit()
    return claimed


def complete_source_file(
    session: Session,
    *,
    source_file_id: uuid.UUID,
    worker_id: str,
    text: str,
    parser_version: str,
    now: datetime,
    model_provider: str,
    model_name: str,
    analysis_max_attempts: int,
) -> None:
    claimed_source = session.get(SourceFile, source_file_id)
    if claimed_source is None:
        return
    job = session.scalar(
        select(JobPosting)
        .where(JobPosting.id == claimed_source.job_posting_id)
        .with_for_update()
    )
    if job is None:
        return
    sources = list(
        session.scalars(
            select(SourceFile)
            .where(SourceFile.job_posting_id == job.id)
            .order_by(SourceFile.sequence_index.asc())
            .with_for_update()
        )
    )
    source_file = next((item for item in sources if item.id == source_file_id), None)
    if (
        source_file is None
        or source_file.parse_status != SourceFileStatus.RUNNING
        or source_file.worker_id != worker_id[:100]
    ):
        return
    source_file.extracted_text = text
    source_file.parse_status = SourceFileStatus.SUCCEEDED
    source_file.parser_version = parser_version
    source_file.error_code = None
    source_file.completed_at = now
    source_file.lease_expires_at = None
    source_file.worker_id = None
    if all(item.parse_status == SourceFileStatus.SUCCEEDED for item in sources):
        texts = [item.extracted_text for item in sources]
        if all(texts):
            job.original_text = SOURCE_TEXT_SEPARATOR.join(text for text in texts if text)
            job.status = JobPostingStatus.DRAFT
            enqueue_ai_analysis_run_locked(
                session,
                job,
                model_provider=model_provider,
                model_name=model_name,
                max_attempts=analysis_max_attempts,
            )
    elif any(item.parse_status == SourceFileStatus.FAILED for item in sources):
        job.status = JobPostingStatus.FAILED
    session.commit()


def fail_or_retry_source_file(
    session: Session,
    *,
    source_file_id: uuid.UUID,
    worker_id: str,
    error_code: str,
    retryable: bool,
    now: datetime,
    retry_delay_seconds: int,
) -> None:
    source_file = session.scalar(
        select(SourceFile)
        .where(
            SourceFile.id == source_file_id,
            SourceFile.parse_status == SourceFileStatus.RUNNING,
            SourceFile.worker_id == worker_id[:100],
        )
        .with_for_update()
    )
    if source_file is None:
        return
    job = session.get(JobPosting, source_file.job_posting_id)
    source_file.error_code = error_code
    source_file.lease_expires_at = None
    source_file.worker_id = None
    if retryable and source_file.attempt_count < source_file.max_attempts:
        source_file.parse_status = SourceFileStatus.PENDING
        delay = retry_delay_seconds * (2 ** (source_file.attempt_count - 1))
        source_file.available_at = now + timedelta(seconds=delay)
        if job is not None:
            job.status = JobPostingStatus.EXTRACTING
    else:
        source_file.parse_status = SourceFileStatus.FAILED
        source_file.completed_at = now
        if job is not None:
            job.status = JobPostingStatus.FAILED
    session.commit()


def execute_claimed_source_file(
    session_factory,
    claimed: ClaimedSourceFile,
    store: ObjectStore,
    *,
    worker_id: str,
    now: datetime | None,
    retry_delay_seconds: int,
    max_chars: int,
    pdf_max_pages: int,
    model_provider: str,
    model_name: str,
    analysis_max_attempts: int,
    file_scanner: FileScanner,
    image_ocr: ImageOcr | None = None,
    pdf_render_scale: float = 2,
    pdf_ocr_max_page_pixels: int = 20_000_000,
    pdf_ocr_max_total_pixels: int = 120_000_000,
) -> None:
    try:
        content = store.read(claimed.object_key)
        file_scanner.scan(content)
        if claimed.detected_media_type in IMAGE_MEDIA_TYPES:
            if image_ocr is None:
                raise DocumentError("image_ocr_unavailable", "Image OCR is unavailable")
            text = image_ocr.extract_text(content)
            parser_version = IMAGE_OCR_VERSION
        else:
            text = parse_document(
                content,
                claimed.detected_media_type,
                max_chars=max_chars,
                pdf_max_pages=pdf_max_pages,
                image_ocr=image_ocr,
                pdf_render_scale=pdf_render_scale,
                pdf_ocr_max_page_pixels=pdf_ocr_max_page_pixels,
                pdf_ocr_max_total_pixels=pdf_ocr_max_total_pixels,
            )
            parser_version = PARSER_VERSION
    except StorageUnavailableError:
        error_code, retryable = "storage_unavailable", True
    except MalwareDetectedError as error:
        error_code, retryable = error.code, error.retryable
        try:
            store.delete(claimed.object_key)
        except StorageUnavailableError:
            logger.error("Could not remove quarantined object after malware detection")
    except DocumentError as error:
        error_code, retryable = error.code, error.retryable
    except Exception:
        error_code, retryable = "document_parse_failed", False
    else:
        with session_factory() as session:
            complete_source_file(
                session,
                source_file_id=claimed.source_file_id,
                worker_id=worker_id,
                text=text,
                parser_version=parser_version,
                now=now or datetime.now(UTC),
                model_provider=model_provider,
                model_name=model_name,
                analysis_max_attempts=analysis_max_attempts,
            )
        return
    with session_factory() as session:
        fail_or_retry_source_file(
            session,
            source_file_id=claimed.source_file_id,
            worker_id=worker_id,
            error_code=error_code,
            retryable=retryable,
            now=now or datetime.now(UTC),
            retry_delay_seconds=retry_delay_seconds,
        )

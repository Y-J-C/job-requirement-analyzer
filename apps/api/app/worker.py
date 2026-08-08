import argparse
import socket
import time
import uuid
from datetime import UTC, datetime

from app.ai.contracts import RequirementAnalyzer
from app.ai.dependencies import build_requirement_analyzer
from app.core.config import Settings, get_settings
from app.core.database import SessionLocal
from app.services.analysis import claim_next_analysis_run, execute_claimed_analysis
from app.services.source_file import claim_next_source_file, execute_claimed_source_file
from app.storage.contracts import ObjectStore
from app.storage.dependencies import get_object_store


def run_source_file_once(
    session_factory,
    store: ObjectStore,
    *,
    worker_id: str,
    now: datetime | None = None,
    lease_seconds: int = 120,
    retry_delay_seconds: int = 5,
    max_chars: int = 100_000,
    pdf_max_pages: int = 50,
) -> bool:
    claimed_at = now or datetime.now(UTC)
    with session_factory() as session:
        claimed = claim_next_source_file(
            session,
            worker_id=worker_id,
            now=claimed_at,
            lease_seconds=lease_seconds,
        )
    if claimed is None:
        return False
    execute_claimed_source_file(
        session_factory,
        claimed,
        store,
        worker_id=worker_id,
        now=now,
        retry_delay_seconds=retry_delay_seconds,
        max_chars=max_chars,
        pdf_max_pages=pdf_max_pages,
    )
    return True


def run_once(
    session_factory,
    analyzer: RequirementAnalyzer,
    *,
    worker_id: str,
    now: datetime | None = None,
    lease_seconds: int = 600,
    retry_delay_seconds: int = 5,
    object_store: ObjectStore | None = None,
    document_lease_seconds: int = 120,
    max_chars: int = 100_000,
    pdf_max_pages: int = 50,
) -> bool:
    if object_store is not None and run_source_file_once(
        session_factory,
        object_store,
        worker_id=worker_id,
        now=now,
        lease_seconds=document_lease_seconds,
        retry_delay_seconds=retry_delay_seconds,
        max_chars=max_chars,
        pdf_max_pages=pdf_max_pages,
    ):
        return True
    claimed_at = now or datetime.now(UTC)
    with session_factory() as session:
        claimed = claim_next_analysis_run(
            session,
            worker_id=worker_id,
            now=claimed_at,
            lease_seconds=lease_seconds,
        )
    if claimed is None:
        return False
    execute_claimed_analysis(
        session_factory,
        claimed,
        analyzer,
        worker_id=worker_id,
        now=now,
        retry_delay_seconds=retry_delay_seconds,
    )
    return True


def run_worker(settings: Settings, *, once: bool = False) -> None:
    analyzer = build_requirement_analyzer(settings)
    object_store = get_object_store()
    worker_id = f"{socket.gethostname()}-{uuid.uuid4().hex[:12]}"
    while True:
        processed = run_once(
            SessionLocal,
            analyzer,
            worker_id=worker_id,
            lease_seconds=settings.analysis_worker_lease_seconds,
            retry_delay_seconds=settings.analysis_worker_retry_delay_seconds,
            object_store=object_store,
            document_lease_seconds=settings.document_worker_lease_seconds,
            max_chars=settings.extracted_text_max_chars,
            pdf_max_pages=settings.pdf_max_pages,
        )
        if once:
            return
        if not processed:
            time.sleep(settings.analysis_worker_poll_seconds)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the durable analysis worker")
    parser.add_argument("--once", action="store_true", help="Process at most one task")
    args = parser.parse_args()
    run_worker(get_settings(), once=args.once)


if __name__ == "__main__":
    main()

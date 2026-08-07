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


def run_once(
    session_factory,
    analyzer: RequirementAnalyzer,
    *,
    worker_id: str,
    now: datetime | None = None,
    lease_seconds: int = 600,
    retry_delay_seconds: int = 5,
) -> bool:
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
    worker_id = f"{socket.gethostname()}-{uuid.uuid4().hex[:12]}"
    while True:
        processed = run_once(
            SessionLocal,
            analyzer,
            worker_id=worker_id,
            lease_seconds=settings.analysis_worker_lease_seconds,
            retry_delay_seconds=settings.analysis_worker_retry_delay_seconds,
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

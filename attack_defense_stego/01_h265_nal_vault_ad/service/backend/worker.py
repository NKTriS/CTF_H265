import os
import time

from app import _connect, _execute, _render_preview, _set_preview_job


SLEEP_SECONDS = float(os.environ.get("WORKER_SLEEP", "2"))
BATCH_SIZE = int(os.environ.get("WORKER_BATCH_SIZE", "8"))


def claim_jobs(limit: int) -> list[str]:
    with _connect() as conn:
        rows = _execute(
            conn,
            """
            SELECT case_id FROM preview_jobs
            WHERE status IN ('queued', 'failed')
            ORDER BY updated_at ASC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
        case_ids = [row["case_id"] for row in rows]
        for case_id in case_ids:
            _execute(
                conn,
                "UPDATE preview_jobs SET status = 'rendering', updated_at = ? WHERE case_id = ?",
                (int(time.time()), case_id),
            )
        conn.commit()
    return case_ids


def main() -> None:
    while True:
        case_ids = claim_jobs(BATCH_SIZE)
        if not case_ids:
            time.sleep(SLEEP_SECONDS)
            continue

        for case_id in case_ids:
            try:
                _render_preview(case_id)
            except Exception as exc:
                _set_preview_job(case_id, "failed", repr(exc))


if __name__ == "__main__":
    main()

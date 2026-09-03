"""Small snapshot helpers for Sales tables."""

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from onyx.db.models import SalesActivity, SalesFollowUpTask, SalesOpportunity


def sales_snapshot(db_session: Session) -> dict[str, int]:
    return {"activities": int(db_session.scalar(select(func.count()).select_from(SalesActivity)) or 0), "tasks": int(db_session.scalar(select(func.count()).select_from(SalesFollowUpTask)) or 0), "opportunities": int(db_session.scalar(select(func.count()).select_from(SalesOpportunity)) or 0)}


def grade_snapshot(before: dict[str, int], after: dict[str, int], expected_changes: dict[str, int]) -> list[str]:
    return [f"{table}: expected change {expected}, observed {after[table] - before[table]}" for table, expected in expected_changes.items() if after[table] - before[table] != expected]

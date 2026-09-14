"""Typed data access for the Enterprise AI Sales Copilot demo."""

from datetime import date
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from onyx.configs.constants import MessageType
from onyx.db.models import (
    ChatMessage,
    ChatSession,
    SalesAccount,
    SalesActivity,
    SalesFollowUpTask,
    SalesOpportunity,
    SalesProduct,
)

_CONFIRMATION_PREFIXES = (
    "confirm",
    "confirmed",
    "yes, confirm",
    "我确认",
    "确认执行",
    "同意执行",
)


def search_accounts(
    db_session: Session, query: str | None = None
) -> list[SalesAccount]:
    statement = select(SalesAccount).order_by(SalesAccount.name)
    if query:
        statement = statement.where(SalesAccount.name.ilike(f"%{query.strip()}%"))
    return list(db_session.scalars(statement))


def get_account(db_session: Session, account_id: int) -> SalesAccount | None:
    return db_session.get(SalesAccount, account_id)


def get_opportunity(
    db_session: Session, opportunity_id: int
) -> SalesOpportunity | None:
    return db_session.get(SalesOpportunity, opportunity_id)


def get_product_information(
    db_session: Session, query: str | None = None
) -> list[SalesProduct]:
    statement = select(SalesProduct).order_by(SalesProduct.name)
    if query:
        statement = statement.where(SalesProduct.name.ilike(f"%{query.strip()}%"))
    return list(db_session.scalars(statement))


def search_opportunities(
    db_session: Session, stage: str | None = None
) -> list[SalesOpportunity]:
    statement = select(SalesOpportunity).order_by(
        SalesOpportunity.expected_revenue_rmb.desc()
    )
    if stage:
        statement = statement.where(SalesOpportunity.stage == stage)
    return list(db_session.scalars(statement))


def get_customer_activities(
    db_session: Session, account_id: int
) -> list[SalesActivity]:
    return list(
        db_session.scalars(
            select(SalesActivity)
            .where(SalesActivity.account_id == account_id)
            .order_by(SalesActivity.occurred_at.desc())
        )
    )


def is_explicit_confirmation_turn(
    db_session: Session,
    *,
    user_id: UUID,
    chat_session_id: UUID,
    preview_user_message_id: int,
    confirmation_user_message_id: int,
) -> bool:
    """Verify that confirmation came from the next explicit user turn."""
    chat_session = db_session.get(ChatSession, chat_session_id)
    preview = db_session.get(ChatMessage, preview_user_message_id)
    confirmation = db_session.get(ChatMessage, confirmation_user_message_id)
    if (
        chat_session is None
        or chat_session.user_id != user_id
        or preview is None
        or confirmation is None
        or preview.chat_session_id != chat_session_id
        or confirmation.chat_session_id != chat_session_id
        or preview.message_type != MessageType.USER
        or confirmation.message_type != MessageType.USER
        or confirmation.parent_message_id is None
    ):
        return False

    assistant = db_session.get(ChatMessage, confirmation.parent_message_id)
    if (
        assistant is None
        or assistant.message_type != MessageType.ASSISTANT
        or assistant.parent_message_id != preview.id
    ):
        return False

    normalized = " ".join(confirmation.message.casefold().split())
    return normalized.startswith(_CONFIRMATION_PREFIXES)


def get_deal_council_context(
    db_session: Session, account_query: str
) -> dict[str, object]:
    """Return all read-only CRM and catalog data needed by one council request."""
    account = db_session.scalar(
        select(SalesAccount).where(
            SalesAccount.name.ilike(f"%{account_query.strip()}%")
        )
    )
    if account is None:
        return {"account": None, "opportunity": None, "activities": [], "products": []}
    opportunity = db_session.scalar(
        select(SalesOpportunity)
        .where(SalesOpportunity.account_id == account.id)
        .order_by(SalesOpportunity.expected_revenue_rmb.desc())
    )
    activities = get_customer_activities(db_session, account.id)
    return {
        "account": account,
        "opportunity": opportunity,
        "activities": activities,
        "products": get_product_information(db_session),
    }


def pipeline_by_industry(db_session: Session) -> list[tuple[str, float]]:
    statement = (
        select(SalesAccount.industry, func.sum(SalesOpportunity.expected_revenue_rmb))
        .join(SalesOpportunity)
        .group_by(SalesAccount.industry)
    )
    return [
        (industry, float(amount)) for industry, amount in db_session.execute(statement)
    ]


def create_follow_up_task(
    db_session: Session,
    account_id: int,
    title: str,
    due_date: date,
    opportunity_id: int | None = None,
) -> SalesFollowUpTask:
    task = SalesFollowUpTask(
        account_id=account_id,
        opportunity_id=opportunity_id,
        title=title,
        due_date=due_date,
        status="open",
    )
    db_session.add(task)
    db_session.commit()
    db_session.refresh(task)
    return task


def update_opportunity_stage(
    db_session: Session, opportunity_id: int, stage: str
) -> SalesOpportunity | None:
    opportunity = db_session.get(SalesOpportunity, opportunity_id)
    if opportunity is None:
        return None
    opportunity.stage = stage
    db_session.commit()
    db_session.refresh(opportunity)
    return opportunity


def add_customer_activity(
    db_session: Session,
    account_id: int,
    summary: str,
    activity_type: str,
    opportunity_id: int | None = None,
) -> SalesActivity:
    activity = SalesActivity(
        account_id=account_id,
        opportunity_id=opportunity_id,
        summary=summary,
        activity_type=activity_type,
    )
    db_session.add(activity)
    db_session.commit()
    db_session.refresh(activity)
    return activity

"""Typed data access for the Enterprise AI Sales Copilot demo."""

from datetime import date

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from onyx.db.models import SalesAccount, SalesActivity, SalesFollowUpTask, SalesOpportunity, SalesProduct


def search_accounts(db_session: Session, query: str | None = None) -> list[SalesAccount]:
    statement = select(SalesAccount).order_by(SalesAccount.name)
    if query:
        statement = statement.where(SalesAccount.name.ilike(f"%{query.strip()}%"))
    return list(db_session.scalars(statement))


def get_account(db_session: Session, account_id: int) -> SalesAccount | None:
    return db_session.get(SalesAccount, account_id)


def get_opportunity(db_session: Session, opportunity_id: int) -> SalesOpportunity | None:
    return db_session.get(SalesOpportunity, opportunity_id)


def get_product_information(db_session: Session, query: str | None = None) -> list[SalesProduct]:
    statement = select(SalesProduct).order_by(SalesProduct.name)
    if query:
        statement = statement.where(SalesProduct.name.ilike(f"%{query.strip()}%"))
    return list(db_session.scalars(statement))


def search_opportunities(db_session: Session, stage: str | None = None) -> list[SalesOpportunity]:
    statement = select(SalesOpportunity).order_by(SalesOpportunity.expected_revenue_rmb.desc())
    if stage:
        statement = statement.where(SalesOpportunity.stage == stage)
    return list(db_session.scalars(statement))


def get_customer_activities(db_session: Session, account_id: int) -> list[SalesActivity]:
    return list(db_session.scalars(select(SalesActivity).where(SalesActivity.account_id == account_id).order_by(SalesActivity.occurred_at.desc())))


def pipeline_by_industry(db_session: Session) -> list[tuple[str, float]]:
    statement = select(SalesAccount.industry, func.sum(SalesOpportunity.expected_revenue_rmb)).join(SalesOpportunity).group_by(SalesAccount.industry)
    return [(industry, float(amount)) for industry, amount in db_session.execute(statement)]


def create_follow_up_task(db_session: Session, account_id: int, title: str, due_date: date, opportunity_id: int | None = None) -> SalesFollowUpTask:
    task = SalesFollowUpTask(account_id=account_id, opportunity_id=opportunity_id, title=title, due_date=due_date, status="open")
    db_session.add(task)
    db_session.commit()
    db_session.refresh(task)
    return task


def update_opportunity_stage(db_session: Session, opportunity_id: int, stage: str) -> SalesOpportunity | None:
    opportunity = db_session.get(SalesOpportunity, opportunity_id)
    if opportunity is None:
        return None
    opportunity.stage = stage
    db_session.commit()
    db_session.refresh(opportunity)
    return opportunity


def add_customer_activity(db_session: Session, account_id: int, summary: str, activity_type: str, opportunity_id: int | None = None) -> SalesActivity:
    activity = SalesActivity(account_id=account_id, opportunity_id=opportunity_id, summary=summary, activity_type=activity_type)
    db_session.add(activity)
    db_session.commit()
    db_session.refresh(activity)
    return activity

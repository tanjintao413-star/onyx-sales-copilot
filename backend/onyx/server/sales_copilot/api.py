from datetime import date
from decimal import Decimal

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from onyx.auth.users import current_user
from onyx.db.engine.sql_engine import get_session
from onyx.db.sales_copilot import (
    add_customer_activity,
    create_follow_up_task,
    get_account,
    get_customer_activities,
    get_product_information,
    pipeline_by_industry,
    search_accounts,
    search_opportunities,
    update_opportunity_stage,
)
from onyx.error_handling.error_codes import OnyxErrorCode
from onyx.error_handling.exceptions import OnyxError
from onyx.sales_copilot.deal_council.models import DealCouncilDecision
from onyx.sales_copilot.deal_council.orchestrator import run_deal_council

router = APIRouter(
    prefix="/sales-copilot",
    tags=["sales-copilot"],
    dependencies=[Depends(current_user)],
)


class AccountResponse(BaseModel):
    id: int
    name: str
    industry: str
    employee_count: int
    region: str
    notes: str | None


class OpportunityResponse(BaseModel):
    id: int
    account_id: int
    name: str
    stage: str
    expected_revenue_rmb: Decimal
    product_name: str
    expected_close_date: date | None


class ActivityResponse(BaseModel):
    id: int
    account_id: int
    opportunity_id: int | None
    activity_type: str
    summary: str


class ProductResponse(BaseModel):
    id: int
    name: str
    edition: str
    description: str


class FollowUpTaskRequest(BaseModel):
    account_id: int = Field(gt=0)
    opportunity_id: int | None = Field(default=None, gt=0)
    title: str = Field(min_length=3, max_length=255)
    due_date: date
    confirmed: bool = False


class OpportunityStageRequest(BaseModel):
    stage: str = Field(min_length=2, max_length=50)
    confirmed: bool = False


class CustomerActivityRequest(BaseModel):
    account_id: int = Field(gt=0)
    opportunity_id: int | None = Field(default=None, gt=0)
    activity_type: str = Field(min_length=2, max_length=50)
    summary: str = Field(min_length=3)
    confirmed: bool = False


class RoiRequest(BaseModel):
    employee_count: int = Field(gt=0)
    average_salary: float = Field(gt=0, description="Annual salary per employee, RMB")
    hours_saved_per_employee: float = Field(ge=0, description="Monthly hours saved")
    automation_rate: float = Field(ge=0, le=1)
    software_cost: float = Field(ge=0, description="Annual software cost, RMB")


class RoiResponse(BaseModel):
    annual_labor_saving: float
    estimated_ai_cost: float
    net_saving: float
    roi: float = Field(description="ROI multiple; 107 means 107x, not 107%")
    payback_period_months: float | None
    formula: str


class DealCouncilRequest(BaseModel):
    request: str = Field(min_length=3, max_length=2000)


def _account(account: object) -> AccountResponse:
    return AccountResponse.model_validate(account, from_attributes=True)


def _opportunity(opportunity: object) -> OpportunityResponse:
    return OpportunityResponse.model_validate(opportunity, from_attributes=True)


@router.get("/accounts")
def search_sales_accounts(query: str | None = None, db_session: Session = Depends(get_session)) -> list[AccountResponse]:
    return [_account(account) for account in search_accounts(db_session, query)]


@router.get("/accounts/{account_id}")
def get_sales_account(account_id: int, db_session: Session = Depends(get_session)) -> AccountResponse:
    account = get_account(db_session, account_id)
    if account is None:
        raise OnyxError(OnyxErrorCode.NOT_FOUND, "Sales account not found")
    return _account(account)


@router.get("/opportunities")
def search_sales_opportunities(stage: str | None = None, db_session: Session = Depends(get_session)) -> list[OpportunityResponse]:
    return [_opportunity(opportunity) for opportunity in search_opportunities(db_session, stage)]


@router.get("/accounts/{account_id}/activities")
def customer_activities(account_id: int, db_session: Session = Depends(get_session)) -> list[ActivityResponse]:
    return [ActivityResponse.model_validate(activity, from_attributes=True) for activity in get_customer_activities(db_session, account_id)]


@router.get("/pipeline")
def sales_pipeline(db_session: Session = Depends(get_session)) -> dict[str, object]:
    rows = pipeline_by_industry(db_session)
    return {"by_industry_rmb": [{"industry": industry, "amount": amount} for industry, amount in rows], "total_rmb": sum(amount for _, amount in rows)}


@router.get("/products")
def product_information(query: str | None = None, db_session: Session = Depends(get_session)) -> list[ProductResponse]:
    return [ProductResponse.model_validate(product, from_attributes=True) for product in get_product_information(db_session, query)]


@router.post("/deal-council")
def evaluate_deal_council(body: DealCouncilRequest, db_session: Session = Depends(get_session)) -> DealCouncilDecision:
    """Return a read-only cross-functional deal decision and action proposals."""
    return run_deal_council(body.request, db_session)


@router.post("/follow-up-tasks")
def create_sales_follow_up_task(body: FollowUpTaskRequest, db_session: Session = Depends(get_session)) -> dict[str, object]:
    if not body.confirmed:
        return {"status": "confirmation_required", "message": "Set confirmed=true to create this follow-up task."}
    if get_account(db_session, body.account_id) is None:
        raise OnyxError(OnyxErrorCode.NOT_FOUND, "Sales account not found")
    task = create_follow_up_task(db_session, body.account_id, body.title, body.due_date, body.opportunity_id)
    return {"status": "created", "task_id": task.id, "title": task.title, "due_date": task.due_date}


@router.patch("/opportunities/{opportunity_id}/stage")
def change_sales_opportunity_stage(opportunity_id: int, body: OpportunityStageRequest, db_session: Session = Depends(get_session)) -> dict[str, object]:
    if not body.confirmed:
        return {"status": "confirmation_required", "message": "Set confirmed=true to update this opportunity."}
    opportunity = update_opportunity_stage(db_session, opportunity_id, body.stage)
    if opportunity is None:
        raise OnyxError(OnyxErrorCode.NOT_FOUND, "Sales opportunity not found")
    return {"status": "updated", "opportunity": _opportunity(opportunity).model_dump(mode="json")}


@router.post("/activities")
def add_sales_customer_activity(body: CustomerActivityRequest, db_session: Session = Depends(get_session)) -> dict[str, object]:
    if not body.confirmed:
        return {"status": "confirmation_required", "message": "Set confirmed=true to add this customer activity."}
    if get_account(db_session, body.account_id) is None:
        raise OnyxError(OnyxErrorCode.NOT_FOUND, "Sales account not found")
    activity = add_customer_activity(db_session, body.account_id, body.summary, body.activity_type, body.opportunity_id)
    return {"status": "created", "activity_id": activity.id}


@router.post("/roi")
def calculate_ai_roi(body: RoiRequest) -> RoiResponse:
    annual_labor_saving = body.employee_count * body.average_salary * (body.hours_saved_per_employee / 160) * 12 * body.automation_rate
    net_saving = annual_labor_saving - body.software_cost
    return RoiResponse(annual_labor_saving=round(annual_labor_saving, 2), estimated_ai_cost=body.software_cost, net_saving=round(net_saving, 2), roi=round(net_saving / body.software_cost, 2) if body.software_cost else 0, payback_period_months=round(body.software_cost / (annual_labor_saving / 12), 1) if annual_labor_saving else None, formula="employees × annual_salary × monthly_hours_saved/160 × 12 × automation_rate")

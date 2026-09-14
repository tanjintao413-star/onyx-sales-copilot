import hashlib
import json
import secrets
from datetime import date
from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, Depends, Header
from pydantic import AliasChoices, BaseModel, Field, model_validator
from sqlalchemy.orm import Session

from onyx.auth.users import current_user
from onyx.db.engine.sql_engine import get_session
from onyx.db.models import User
from onyx.db.sales_copilot import (
    add_customer_activity,
    create_follow_up_task,
    get_account,
    get_customer_activities,
    get_product_information,
    is_explicit_confirmation_turn,
    pipeline_by_industry,
    search_accounts,
    search_opportunities,
    update_opportunity_stage,
)
from onyx.error_handling.error_codes import OnyxErrorCode
from onyx.error_handling.exceptions import OnyxError
from onyx.redis.redis_pool import get_redis_client
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
    opportunity_id: int | None = Field(
        default=None,
        gt=0,
        validation_alias=AliasChoices("opportunity_id", "related_opportunity_id"),
    )
    title: str = Field(min_length=3, max_length=255)
    due_date: date
    confirmed: bool = False
    confirmation_token: str | None = Field(default=None, exclude=True)


class OpportunityStageRequest(BaseModel):
    stage: str = Field(min_length=2, max_length=50)
    confirmed: bool = False
    confirmation_token: str | None = Field(default=None, exclude=True)


class CustomerActivityRequest(BaseModel):
    account_id: int = Field(gt=0)
    opportunity_id: int | None = Field(default=None, gt=0)
    activity_type: str = Field(min_length=2, max_length=50)
    summary: str = Field(min_length=3)
    confirmed: bool = False
    confirmation_token: str | None = Field(default=None, exclude=True)


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
    request: str | dict[str, object] = Field(
        description=(
            "The user's complete decision request. A plain string is preferred; a "
            "structured tool context is also accepted. Preserve intent terms such as "
            "PoC, product fit, private deployment, or stage because they determine "
            "which specialists participate."
        ),
    )

    @model_validator(mode="before")
    @classmethod
    def accept_native_tool_arguments(cls, value: object) -> object:
        """Accept the flat argument object produced by the OpenAPI custom tool.

        FastAPI documents this endpoint with a ``request`` envelope, while the
        native tool call supplies the structured decision context as its top-level
        arguments. Keep the documented HTTP form and normalize only that tool form.
        """
        if isinstance(value, dict) and "request" not in value:
            return {"request": value}
        return value

    def routing_text(self) -> str:
        council_intent = "跨部门 PoC 是否推进评估"
        if isinstance(self.request, str):
            return f"{council_intent} {self.request}"
        context = " ".join(str(value) for value in self.request.values())
        return f"{council_intent} {context}"

    def account_id(self) -> int | None:
        if not isinstance(self.request, dict):
            return None
        value = self.request.get("account_id")
        return value if isinstance(value, int) and value > 0 else None


def _account(account: object) -> AccountResponse:
    return AccountResponse.model_validate(account, from_attributes=True)


def _opportunity(opportunity: object) -> OpportunityResponse:
    return OpportunityResponse.model_validate(opportunity, from_attributes=True)


_CONFIRMATION_TTL_SECONDS = 15 * 60
_CONFIRMATION_KEY_PREFIX = "sales-copilot:confirmation:"
_CONFIRMATION_LOOKUP_PREFIX = "sales-copilot:confirmation-lookup:"


def _confirmation_payload(operation: str, user: User, values: dict[str, object]) -> str:
    canonical = json.dumps(
        {"operation": operation, "user_id": str(user.id), "values": values},
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )
    return hashlib.sha256(canonical.encode()).hexdigest()


def _confirmation_lookup_key(
    operation: str, user: User, session_id: UUID, values: dict[str, object]
) -> str:
    return (
        f"{_CONFIRMATION_LOOKUP_PREFIX}{operation}:{user.id}:{session_id}:"
        f"{_confirmation_payload(operation, user, values)}"
    )


def _confirmation_context(
    chat_session_id: str | None, user_message_id: int | None
) -> tuple[UUID, int]:
    if not chat_session_id or user_message_id is None:
        raise OnyxError(
            OnyxErrorCode.BAD_REQUEST,
            "A native Onyx chat session and user message are required for mutation confirmation",
        )
    try:
        return UUID(chat_session_id), user_message_id
    except ValueError as error:
        raise OnyxError(
            OnyxErrorCode.BAD_REQUEST, "Invalid Onyx chat confirmation context"
        ) from error


def _preview_confirmation(
    operation: str,
    user: User,
    values: dict[str, object],
    chat_session_id: str | None,
    user_message_id: int | None,
) -> dict[str, object]:
    session_id, message_id = _confirmation_context(chat_session_id, user_message_id)
    token = secrets.token_urlsafe(32)
    record = {
        "payload_hash": _confirmation_payload(operation, user, values),
        "chat_session_id": str(session_id),
        "preview_user_message_id": message_id,
    }
    get_redis_client().set(
        f"{_CONFIRMATION_KEY_PREFIX}{token}",
        json.dumps(record, separators=(",", ":")),
        ex=_CONFIRMATION_TTL_SECONDS,
    )
    get_redis_client().set(
        _confirmation_lookup_key(operation, user, session_id, values),
        token,
        ex=_CONFIRMATION_TTL_SECONDS,
    )
    return {
        "status": "confirmation_required",
        "message": "Ask the user to explicitly confirm this exact mutation, then retry with confirmed=true and the confirmation_token.",
        "confirmation_token": token,
    }


def _consume_confirmation(
    operation: str,
    user: User,
    values: dict[str, object],
    token: str | None,
    chat_session_id: str | None,
    user_message_id: int | None,
    db_session: Session,
) -> None:
    session_id, message_id = _confirmation_context(chat_session_id, user_message_id)
    redis = get_redis_client()
    lookup_key = _confirmation_lookup_key(operation, user, session_id, values)
    if not token:
        token = redis.get(lookup_key)
        if isinstance(token, bytes):
            token = token.decode()
    if not token:
        raise OnyxError(
            OnyxErrorCode.BAD_REQUEST,
            "A valid confirmation_token from the preview step is required",
        )
    ticket_key = f"{_CONFIRMATION_KEY_PREFIX}{token}"
    stored = redis.get(ticket_key)
    if stored is None:
        raise OnyxError(
            OnyxErrorCode.BAD_REQUEST,
            "Confirmation token is expired, already used, or does not match this mutation",
        )
    try:
        record = json.loads(stored)
        expected = _confirmation_payload(operation, user, values)
        payload_matches = secrets.compare_digest(record["payload_hash"], expected)
        preview_message_id = int(record["preview_user_message_id"])
        ticket_session_id = UUID(record["chat_session_id"])
    except (KeyError, TypeError, ValueError, json.JSONDecodeError) as error:
        raise OnyxError(
            OnyxErrorCode.BAD_REQUEST, "Invalid confirmation ticket"
        ) from error
    if (
        not payload_matches
        or ticket_session_id != session_id
        or not is_explicit_confirmation_turn(
            db_session,
            user_id=user.id,
            chat_session_id=session_id,
            preview_user_message_id=preview_message_id,
            confirmation_user_message_id=message_id,
        )
    ):
        raise OnyxError(
            OnyxErrorCode.BAD_REQUEST,
            "Confirmation requires an explicit subsequent user message for this exact mutation",
        )
    if redis.getdel(ticket_key) is None:
        raise OnyxError(
            OnyxErrorCode.BAD_REQUEST,
            "Confirmation token is expired, already used, or does not match this mutation",
        )
    redis.delete(lookup_key)


@router.get("/accounts")
def search_sales_accounts(
    query: str | None = None, db_session: Session = Depends(get_session)
) -> list[AccountResponse]:
    return [_account(account) for account in search_accounts(db_session, query)]


@router.get("/accounts/{account_id}")
def get_sales_account(
    account_id: int, db_session: Session = Depends(get_session)
) -> AccountResponse:
    account = get_account(db_session, account_id)
    if account is None:
        raise OnyxError(OnyxErrorCode.NOT_FOUND, "Sales account not found")
    return _account(account)


@router.get("/opportunities")
def search_sales_opportunities(
    stage: str | None = None, db_session: Session = Depends(get_session)
) -> list[OpportunityResponse]:
    return [
        _opportunity(opportunity)
        for opportunity in search_opportunities(db_session, stage)
    ]


@router.get("/accounts/{account_id}/activities")
def customer_activities(
    account_id: int, db_session: Session = Depends(get_session)
) -> list[ActivityResponse]:
    return [
        ActivityResponse.model_validate(activity, from_attributes=True)
        for activity in get_customer_activities(db_session, account_id)
    ]


@router.get("/pipeline")
def sales_pipeline(db_session: Session = Depends(get_session)) -> dict[str, object]:
    rows = pipeline_by_industry(db_session)
    return {
        "by_industry_rmb": [
            {"industry": industry, "amount": amount} for industry, amount in rows
        ],
        "total_rmb": sum(amount for _, amount in rows),
    }


@router.get("/products")
def product_information(
    query: str | None = None, db_session: Session = Depends(get_session)
) -> list[ProductResponse]:
    return [
        ProductResponse.model_validate(product, from_attributes=True)
        for product in get_product_information(db_session, query)
    ]


@router.post("/deal-council")
def evaluate_deal_council(
    body: DealCouncilRequest, db_session: Session = Depends(get_session)
) -> DealCouncilDecision:
    """Route the full request to read-only Sales/Product/Technical specialists."""
    routing_text = body.routing_text()
    if account_id := body.account_id():
        account = get_account(db_session, account_id)
        if account is None:
            raise OnyxError(OnyxErrorCode.NOT_FOUND, "Sales account not found")
        routing_text = f"{routing_text} {account.name}"
    return run_deal_council(routing_text, db_session)


@router.post("/follow-up-tasks")
def create_sales_follow_up_task(
    body: FollowUpTaskRequest,
    user: User = Depends(current_user),
    db_session: Session = Depends(get_session),
    chat_session_id: str | None = Header(default=None, alias="X-Onyx-Chat-Session-ID"),
    user_message_id: int | None = Header(default=None, alias="X-Onyx-User-Message-ID"),
) -> dict[str, object]:
    values = body.model_dump(exclude={"confirmed", "confirmation_token"}, mode="json")
    if not body.confirmed:
        return _preview_confirmation(
            "create_follow_up_task",
            user,
            values,
            chat_session_id,
            user_message_id,
        )
    _consume_confirmation(
        "create_follow_up_task",
        user,
        values,
        body.confirmation_token,
        chat_session_id,
        user_message_id,
        db_session,
    )
    if get_account(db_session, body.account_id) is None:
        raise OnyxError(OnyxErrorCode.NOT_FOUND, "Sales account not found")
    task = create_follow_up_task(
        db_session, body.account_id, body.title, body.due_date, body.opportunity_id
    )
    return {
        "status": "created",
        "task_id": task.id,
        "title": task.title,
        "due_date": task.due_date,
    }


@router.patch("/opportunities/{opportunity_id}/stage")
def change_sales_opportunity_stage(
    opportunity_id: int,
    body: OpportunityStageRequest,
    user: User = Depends(current_user),
    db_session: Session = Depends(get_session),
    chat_session_id: str | None = Header(default=None, alias="X-Onyx-Chat-Session-ID"),
    user_message_id: int | None = Header(default=None, alias="X-Onyx-User-Message-ID"),
) -> dict[str, object]:
    values = {
        "opportunity_id": opportunity_id,
        **body.model_dump(exclude={"confirmed", "confirmation_token"}),
    }
    if not body.confirmed:
        return _preview_confirmation(
            "update_opportunity_stage",
            user,
            values,
            chat_session_id,
            user_message_id,
        )
    _consume_confirmation(
        "update_opportunity_stage",
        user,
        values,
        body.confirmation_token,
        chat_session_id,
        user_message_id,
        db_session,
    )
    opportunity = update_opportunity_stage(db_session, opportunity_id, body.stage)
    if opportunity is None:
        raise OnyxError(OnyxErrorCode.NOT_FOUND, "Sales opportunity not found")
    return {
        "status": "updated",
        "opportunity": _opportunity(opportunity).model_dump(mode="json"),
    }


@router.post("/activities")
def add_sales_customer_activity(
    body: CustomerActivityRequest,
    user: User = Depends(current_user),
    db_session: Session = Depends(get_session),
    chat_session_id: str | None = Header(default=None, alias="X-Onyx-Chat-Session-ID"),
    user_message_id: int | None = Header(default=None, alias="X-Onyx-User-Message-ID"),
) -> dict[str, object]:
    values = body.model_dump(exclude={"confirmed", "confirmation_token"})
    if not body.confirmed:
        return _preview_confirmation(
            "add_customer_activity",
            user,
            values,
            chat_session_id,
            user_message_id,
        )
    _consume_confirmation(
        "add_customer_activity",
        user,
        values,
        body.confirmation_token,
        chat_session_id,
        user_message_id,
        db_session,
    )
    if get_account(db_session, body.account_id) is None:
        raise OnyxError(OnyxErrorCode.NOT_FOUND, "Sales account not found")
    activity = add_customer_activity(
        db_session,
        body.account_id,
        body.summary,
        body.activity_type,
        body.opportunity_id,
    )
    return {"status": "created", "activity_id": activity.id}


@router.post("/roi")
def calculate_ai_roi(body: RoiRequest) -> RoiResponse:
    annual_labor_saving = (
        body.employee_count
        * body.average_salary
        * (body.hours_saved_per_employee / 160)
        * 12
        * body.automation_rate
    )
    net_saving = annual_labor_saving - body.software_cost
    return RoiResponse(
        annual_labor_saving=round(annual_labor_saving, 2),
        estimated_ai_cost=body.software_cost,
        net_saving=round(net_saving, 2),
        roi=round(net_saving / body.software_cost, 2) if body.software_cost else 0,
        payback_period_months=round(body.software_cost / (annual_labor_saving / 12), 1)
        if annual_labor_saving
        else None,
        formula="employees × annual_salary × monthly_hours_saved/160 × 12 × automation_rate",
    )

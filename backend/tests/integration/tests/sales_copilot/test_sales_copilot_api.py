"""PostgreSQL-backed Sales Copilot API checks.

These tests use the standard Onyx integration TestClient, authentication fixtures,
migration fixture, and reset fixture. They do not mock the API or database layer.
"""

from uuid import UUID

import pytest
from scripts.seed_sales_copilot_demo import main as seed_sales_demo
from sqlalchemy import func, select

from onyx.configs.constants import MessageType
from onyx.db.chat import (
    create_chat_session,
    create_new_chat_message,
    get_or_create_root_message,
)
from onyx.db.engine.sql_engine import get_session_with_current_tenant
from onyx.db.models import (
    ChatMessage,
    SalesAccount,
    SalesActivity,
    SalesFollowUpTask,
    SalesOpportunity,
    SalesProduct,
)
from tests.integration.common_utils.constants import API_SERVER_URL
from tests.integration.common_utils.http_client import client
from tests.integration.common_utils.test_models import DATestUser


@pytest.fixture
def sales_data(reset: None, admin_user: DATestUser) -> dict[str, int]:  # noqa: ARG001
    seed_sales_demo()
    with get_session_with_current_tenant() as session:
        account = session.scalar(
            select(SalesAccount).where(SalesAccount.name == "星海科技")
        )
        assert account is not None
        opportunity = session.scalar(
            select(SalesOpportunity).where(SalesOpportunity.account_id == account.id)
        )
        assert opportunity is not None
        return {"account_id": account.id, "opportunity_id": opportunity.id}


def _count(model: type[SalesFollowUpTask] | type[SalesActivity]) -> int:
    with get_session_with_current_tenant() as session:
        return int(session.scalar(select(func.count()).select_from(model)) or 0)


def _preview_turn_headers(
    admin_user: DATestUser, message: str
) -> tuple[dict[str, str], UUID, int]:
    with get_session_with_current_tenant() as session:
        chat_session = create_chat_session(
            db_session=session,
            description="Sales mutation confirmation integration",
            user_id=UUID(admin_user.id),
            persona_id=None,
        )
        root = get_or_create_root_message(chat_session.id, session)
        user_message = create_new_chat_message(
            chat_session_id=chat_session.id,
            parent_message=root,
            message=message,
            token_count=1,
            message_type=MessageType.USER,
            db_session=session,
        )
    headers = {
        **admin_user.headers,
        "X-Onyx-Chat-Session-ID": str(chat_session.id),
        "X-Onyx-User-Message-ID": str(user_message.id),
    }
    return headers, chat_session.id, user_message.id


def _confirmation_turn_headers(
    admin_user: DATestUser,
    chat_session_id: UUID,
    preview_user_message_id: int,
    message: str = "我确认执行刚才的精确变更",
) -> dict[str, str]:
    with get_session_with_current_tenant() as session:
        preview_message = session.get(ChatMessage, preview_user_message_id)
        assert preview_message is not None
        assistant = create_new_chat_message(
            chat_session_id=chat_session_id,
            parent_message=preview_message,
            message="Please confirm the preview.",
            token_count=1,
            message_type=MessageType.ASSISTANT,
            db_session=session,
        )
        confirmation = create_new_chat_message(
            chat_session_id=chat_session_id,
            parent_message=assistant,
            message=message,
            token_count=1,
            message_type=MessageType.USER,
            db_session=session,
        )
    return {
        **admin_user.headers,
        "X-Onyx-Chat-Session-ID": str(chat_session_id),
        "X-Onyx-User-Message-ID": str(confirmation.id),
    }


def test_sales_reads_use_seeded_postgres_data(
    sales_data: dict[str, int], admin_user: DATestUser
) -> None:
    accounts = client.get(
        f"{API_SERVER_URL}/sales-copilot/accounts?query=星海",
        headers=admin_user.headers,
    )
    pipeline = client.get(
        f"{API_SERVER_URL}/sales-copilot/pipeline", headers=admin_user.headers
    )
    activities = client.get(
        f"{API_SERVER_URL}/sales-copilot/accounts/{sales_data['account_id']}/activities",
        headers=admin_user.headers,
    )
    assert accounts.status_code == pipeline.status_code == activities.status_code == 200
    assert accounts.json()[0]["name"] == "星海科技"
    assert pipeline.json()["total_rmb"] > 0
    assert len(activities.json()) == 3


def test_sales_api_rejects_anonymous_request() -> None:
    response = client.get(f"{API_SERVER_URL}/sales-copilot/accounts")
    assert response.status_code != 200


def test_task_preview_and_confirmation_change_postgres_once(
    sales_data: dict[str, int], admin_user: DATestUser
) -> None:
    before = _count(SalesFollowUpTask)
    body = {
        "account_id": sales_data["account_id"],
        "related_opportunity_id": sales_data["opportunity_id"],
        "title": "Harness PoC follow-up",
        "due_date": "2026-09-04",
    }
    preview_headers, chat_session_id, preview_message_id = _preview_turn_headers(
        admin_user, "Preview the Sales follow-up task"
    )
    preview = client.post(
        f"{API_SERVER_URL}/sales-copilot/follow-up-tasks",
        json=body,
        headers=preview_headers,
    )
    assert preview.status_code == 200
    assert preview.json()["status"] == "confirmation_required"
    assert _count(SalesFollowUpTask) == before
    confirmation_headers = _confirmation_turn_headers(
        admin_user, chat_session_id, preview_message_id
    )
    confirmed = client.post(
        f"{API_SERVER_URL}/sales-copilot/follow-up-tasks",
        json={
            **body,
            "confirmed": True,
            "confirmation_token": preview.json()["confirmation_token"],
        },
        headers=confirmation_headers,
    )
    assert confirmed.status_code == 200
    assert confirmed.json()["status"] == "created"
    assert _count(SalesFollowUpTask) == before + 1
    with get_session_with_current_tenant() as session:
        task = session.get(SalesFollowUpTask, confirmed.json()["task_id"])
        assert task is not None
        assert task.opportunity_id == sales_data["opportunity_id"]


def test_stage_and_activity_previews_preserve_postgres(
    sales_data: dict[str, int], admin_user: DATestUser
) -> None:
    with get_session_with_current_tenant() as session:
        stage_before = session.get(SalesOpportunity, sales_data["opportunity_id"]).stage
    activities_before = _count(SalesActivity)
    preview_headers, _, _ = _preview_turn_headers(
        admin_user, "Preview stage and activity changes"
    )
    stage = client.patch(
        f"{API_SERVER_URL}/sales-copilot/opportunities/{sales_data['opportunity_id']}/stage",
        json={"stage": "Closed Won"},
        headers=preview_headers,
    )
    activity = client.post(
        f"{API_SERVER_URL}/sales-copilot/activities",
        json={
            "account_id": sales_data["account_id"],
            "activity_type": "call",
            "summary": "Harness call",
        },
        headers=preview_headers,
    )
    assert (
        stage.json()["status"] == activity.json()["status"] == "confirmation_required"
    )
    with get_session_with_current_tenant() as session:
        assert (
            session.get(SalesOpportunity, sales_data["opportunity_id"]).stage
            == stage_before
        )
    assert _count(SalesActivity) == activities_before


def test_confirmed_stage_and_activity_persist(
    sales_data: dict[str, int], admin_user: DATestUser
) -> None:
    stage_body = {"stage": "Proposal"}
    preview_headers, chat_session_id, preview_message_id = _preview_turn_headers(
        admin_user, "Preview stage and activity changes"
    )
    stage_preview = client.patch(
        f"{API_SERVER_URL}/sales-copilot/opportunities/{sales_data['opportunity_id']}/stage",
        json=stage_body,
        headers=preview_headers,
    )
    activities_before = _count(SalesActivity)
    activity_body = {
        "account_id": sales_data["account_id"],
        "activity_type": "call",
        "summary": "Harness confirmed call",
    }
    activity_preview = client.post(
        f"{API_SERVER_URL}/sales-copilot/activities",
        json=activity_body,
        headers=preview_headers,
    )
    confirmation_headers = _confirmation_turn_headers(
        admin_user, chat_session_id, preview_message_id
    )
    stage = client.patch(
        f"{API_SERVER_URL}/sales-copilot/opportunities/{sales_data['opportunity_id']}/stage",
        json={
            **stage_body,
            "confirmed": True,
            "confirmation_token": stage_preview.json()["confirmation_token"],
        },
        headers=confirmation_headers,
    )
    activity = client.post(
        f"{API_SERVER_URL}/sales-copilot/activities",
        json={
            **activity_body,
            "confirmed": True,
            "confirmation_token": activity_preview.json()["confirmation_token"],
        },
        headers=confirmation_headers,
    )
    assert stage.json()["status"] == "updated"
    assert activity.json()["status"] == "created"
    with get_session_with_current_tenant() as session:
        assert (
            session.get(SalesOpportunity, sales_data["opportunity_id"]).stage
            == "Proposal"
        )
    assert _count(SalesActivity) == activities_before + 1


def test_confirmed_mutation_without_preview_token_is_rejected(
    sales_data: dict[str, int], admin_user: DATestUser
) -> None:
    before = _count(SalesFollowUpTask)
    response = client.post(
        f"{API_SERVER_URL}/sales-copilot/follow-up-tasks",
        json={
            "account_id": sales_data["account_id"],
            "title": "Injected confirmation",
            "due_date": "2026-09-05",
            "confirmed": True,
        },
        headers=admin_user.headers,
    )
    assert response.status_code == 400
    assert _count(SalesFollowUpTask) == before


def test_same_user_turn_cannot_consume_preview_ticket(
    sales_data: dict[str, int], admin_user: DATestUser
) -> None:
    before = _count(SalesFollowUpTask)
    body = {
        "account_id": sales_data["account_id"],
        "opportunity_id": sales_data["opportunity_id"],
        "title": "Same-turn injected confirmation",
        "due_date": "2026-09-05",
    }
    same_turn_headers, _, _ = _preview_turn_headers(
        admin_user, "Preview but do not confirm this task"
    )
    preview = client.post(
        f"{API_SERVER_URL}/sales-copilot/follow-up-tasks",
        json=body,
        headers=same_turn_headers,
    )
    assert preview.status_code == 200
    attack = client.post(
        f"{API_SERVER_URL}/sales-copilot/follow-up-tasks",
        json={
            **body,
            "confirmed": True,
            "confirmation_token": preview.json()["confirmation_token"],
        },
        headers=same_turn_headers,
    )
    assert attack.status_code == 400
    assert _count(SalesFollowUpTask) == before


def _benchmark_snapshot() -> tuple[object, ...]:
    with get_session_with_current_tenant() as session:
        accounts = tuple(
            session.execute(
                select(
                    SalesAccount.name,
                    SalesAccount.industry,
                    SalesAccount.employee_count,
                    SalesAccount.region,
                    SalesAccount.notes,
                )
                .where(SalesAccount.name.in_(("星海科技", "星海科技（苏州）")))
                .order_by(SalesAccount.name)
            ).all()
        )
        opportunities = tuple(
            session.execute(
                select(
                    SalesAccount.name,
                    SalesOpportunity.name,
                    SalesOpportunity.stage,
                    SalesOpportunity.expected_revenue_rmb,
                    SalesOpportunity.product_name,
                    SalesOpportunity.expected_close_date,
                )
                .join(SalesAccount)
                .where(SalesAccount.name == "星海科技")
                .order_by(SalesOpportunity.name)
            ).all()
        )
        activities = tuple(
            session.execute(
                select(
                    SalesActivity.activity_type,
                    SalesActivity.summary,
                    SalesActivity.occurred_at,
                )
                .join(SalesAccount)
                .where(SalesAccount.name == "星海科技")
                .order_by(SalesActivity.occurred_at)
            ).all()
        )
        products = tuple(
            session.execute(
                select(
                    SalesProduct.name,
                    SalesProduct.edition,
                    SalesProduct.description,
                )
                .where(
                    SalesProduct.name.in_(
                        (
                            "Onyx Enterprise Agent",
                            "Onyx Private Deployment",
                            "Onyx Knowledge Search",
                        )
                    )
                )
                .order_by(SalesProduct.name)
            ).all()
        )
        tasks = int(
            session.scalar(
                select(func.count())
                .select_from(SalesFollowUpTask)
                .join(SalesAccount)
                .where(SalesAccount.name == "星海科技")
            )
            or 0
        )
    return accounts, opportunities, activities, products, tasks


def test_benchmark_reset_restores_only_seed_managed_crm_state(
    reset: None, admin_user: DATestUser  # noqa: ARG001
) -> None:
    seed_sales_demo()
    with get_session_with_current_tenant() as session:
        account = session.scalar(
            select(SalesAccount).where(SalesAccount.name == "星海科技")
        )
        assert account is not None
        opportunity = session.scalar(
            select(SalesOpportunity).where(
                SalesOpportunity.account_id == account.id,
                SalesOpportunity.name == "企业知识 Agent 项目",
            )
        )
        assert opportunity is not None
        opportunity.stage = "Won"
        session.add(
            SalesFollowUpTask(
                account_id=account.id,
                opportunity_id=opportunity.id,
                title="Benchmark reset task",
                due_date=opportunity.expected_close_date,
                status="open",
            )
        )
        session.add(
            SalesActivity(
                account_id=account.id,
                opportunity_id=opportunity.id,
                activity_type="call",
                summary="Benchmark reset activity",
            )
        )
        non_benchmark = SalesAccount(
            name="FINAL-FREEZE Non-Benchmark Account",
            industry="Test",
            employee_count=1,
            region="Test",
            notes="Must survive benchmark reset.",
        )
        session.add(non_benchmark)
        session.flush()
        session.add(
            SalesFollowUpTask(
                account_id=non_benchmark.id,
                title="Non-benchmark task",
                due_date=opportunity.expected_close_date,
                status="open",
            )
        )
        session.commit()

    seed_sales_demo(reset_benchmark_state=True)
    first_snapshot = _benchmark_snapshot()
    with get_session_with_current_tenant() as session:
        restored = session.scalar(
            select(SalesOpportunity).where(
                SalesOpportunity.name == "企业知识 Agent 项目"
            )
        )
        assert restored is not None
        assert restored.stage == "Proposal"
        assert session.scalar(
            select(SalesAccount).where(
                SalesAccount.name == "FINAL-FREEZE Non-Benchmark Account"
            )
        ) is not None
        assert int(
            session.scalar(
                select(func.count())
                .select_from(SalesFollowUpTask)
                .join(SalesAccount)
                .where(SalesAccount.name == "FINAL-FREEZE Non-Benchmark Account")
            )
            or 0
        ) == 1

    seed_sales_demo(reset_benchmark_state=True)
    assert _benchmark_snapshot() == first_snapshot

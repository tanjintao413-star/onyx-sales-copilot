"""PostgreSQL-backed Sales Copilot API checks.

These tests use the standard Onyx integration TestClient, authentication fixtures,
migration fixture, and reset fixture. They do not mock the API or database layer.
"""

from datetime import date

import pytest
from sqlalchemy import func, select

from onyx.db.engine.sql_engine import get_session_with_current_tenant
from onyx.db.models import SalesAccount, SalesActivity, SalesFollowUpTask, SalesOpportunity
from scripts.seed_sales_copilot_demo import main as seed_sales_demo
from tests.integration.common_utils.constants import API_SERVER_URL
from tests.integration.common_utils.http_client import client
from tests.integration.common_utils.test_models import DATestUser


@pytest.fixture
def sales_data(reset: None, admin_user: DATestUser) -> dict[str, int]:  # noqa: ARG001
    seed_sales_demo()
    with get_session_with_current_tenant() as session:
        account = session.scalar(select(SalesAccount).where(SalesAccount.name == "星海科技"))
        assert account is not None
        opportunity = session.scalar(select(SalesOpportunity).where(SalesOpportunity.account_id == account.id))
        assert opportunity is not None
        return {"account_id": account.id, "opportunity_id": opportunity.id}


def _count(model: type[SalesFollowUpTask] | type[SalesActivity]) -> int:
    with get_session_with_current_tenant() as session:
        return int(session.scalar(select(func.count()).select_from(model)) or 0)


def test_sales_reads_use_seeded_postgres_data(sales_data: dict[str, int], admin_user: DATestUser) -> None:
    accounts = client.get(f"{API_SERVER_URL}/sales-copilot/accounts?query=星海", headers=admin_user.headers)
    pipeline = client.get(f"{API_SERVER_URL}/sales-copilot/pipeline", headers=admin_user.headers)
    activities = client.get(f"{API_SERVER_URL}/sales-copilot/accounts/{sales_data['account_id']}/activities", headers=admin_user.headers)
    assert accounts.status_code == pipeline.status_code == activities.status_code == 200
    assert accounts.json()[0]["name"] == "星海科技"
    assert pipeline.json()["total_rmb"] > 0
    assert len(activities.json()) == 2


def test_sales_api_rejects_anonymous_request() -> None:
    response = client.get(f"{API_SERVER_URL}/sales-copilot/accounts")
    assert response.status_code != 200


def test_task_preview_and_confirmation_change_postgres_once(sales_data: dict[str, int], admin_user: DATestUser) -> None:
    before = _count(SalesFollowUpTask)
    body = {"account_id": sales_data["account_id"], "title": "Harness PoC follow-up", "due_date": "2026-09-04"}
    preview = client.post(f"{API_SERVER_URL}/sales-copilot/follow-up-tasks", json=body, headers=admin_user.headers)
    assert preview.status_code == 200
    assert preview.json()["status"] == "confirmation_required"
    assert _count(SalesFollowUpTask) == before
    confirmed = client.post(f"{API_SERVER_URL}/sales-copilot/follow-up-tasks", json={**body, "confirmed": True}, headers=admin_user.headers)
    assert confirmed.status_code == 200
    assert confirmed.json()["status"] == "created"
    assert _count(SalesFollowUpTask) == before + 1


def test_stage_and_activity_previews_preserve_postgres(sales_data: dict[str, int], admin_user: DATestUser) -> None:
    with get_session_with_current_tenant() as session:
        stage_before = session.get(SalesOpportunity, sales_data["opportunity_id"]).stage
    activities_before = _count(SalesActivity)
    stage = client.patch(f"{API_SERVER_URL}/sales-copilot/opportunities/{sales_data['opportunity_id']}/stage", json={"stage": "Closed Won"}, headers=admin_user.headers)
    activity = client.post(f"{API_SERVER_URL}/sales-copilot/activities", json={"account_id": sales_data["account_id"], "activity_type": "call", "summary": "Harness call"}, headers=admin_user.headers)
    assert stage.json()["status"] == activity.json()["status"] == "confirmation_required"
    with get_session_with_current_tenant() as session:
        assert session.get(SalesOpportunity, sales_data["opportunity_id"]).stage == stage_before
    assert _count(SalesActivity) == activities_before


def test_confirmed_stage_and_activity_persist(sales_data: dict[str, int], admin_user: DATestUser) -> None:
    stage = client.patch(f"{API_SERVER_URL}/sales-copilot/opportunities/{sales_data['opportunity_id']}/stage", json={"stage": "Proposal", "confirmed": True}, headers=admin_user.headers)
    activities_before = _count(SalesActivity)
    activity = client.post(f"{API_SERVER_URL}/sales-copilot/activities", json={"account_id": sales_data["account_id"], "activity_type": "call", "summary": "Harness confirmed call", "confirmed": True}, headers=admin_user.headers)
    assert stage.json()["status"] == "updated"
    assert activity.json()["status"] == "created"
    with get_session_with_current_tenant() as session:
        assert session.get(SalesOpportunity, sales_data["opportunity_id"]).stage == "Proposal"
    assert _count(SalesActivity) == activities_before + 1

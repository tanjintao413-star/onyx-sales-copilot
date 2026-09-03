"""PostgreSQL-backed read-only safety checks for the Deal Council API."""

import pytest
from scripts.seed_sales_copilot_demo import main as seed_sales_demo
from sqlalchemy import func, select

from onyx.db.engine.sql_engine import get_session_with_current_tenant
from onyx.db.models import (
    SalesAccount,
    SalesActivity,
    SalesFollowUpTask,
    SalesOpportunity,
)
from tests.integration.common_utils.constants import API_SERVER_URL
from tests.integration.common_utils.http_client import client
from tests.integration.common_utils.test_models import DATestUser


@pytest.fixture
def seeded_sales(reset: None, admin_user: DATestUser) -> tuple[int, int]:  # noqa: ARG001
    seed_sales_demo()
    with get_session_with_current_tenant() as session:
        account = session.scalar(select(SalesAccount).where(SalesAccount.name == "星海科技"))
        assert account is not None
        opportunity = session.scalar(select(SalesOpportunity).where(SalesOpportunity.account_id == account.id))
        assert opportunity is not None
        return account.id, opportunity.id


def _snapshot(opportunity_id: int) -> tuple[int, int, str]:
    with get_session_with_current_tenant() as session:
        task_count = int(session.scalar(select(func.count()).select_from(SalesFollowUpTask)) or 0)
        activity_count = int(session.scalar(select(func.count()).select_from(SalesActivity)) or 0)
        opportunity = session.get(SalesOpportunity, opportunity_id)
        assert opportunity is not None
        return task_count, activity_count, opportunity.stage


def test_deal_council_is_read_only_and_preserves_document_provenance(seeded_sales: tuple[int, int], admin_user: DATestUser) -> None:
    _account_id, opportunity_id = seeded_sales
    before = _snapshot(opportunity_id)
    response = client.post(f"{API_SERVER_URL}/sales-copilot/deal-council", json={"request": "星海科技是否应该推进 PoC？请从销售、产品和技术角度评估。"}, headers=admin_user.headers)
    assert response.status_code == 200
    payload = response.json()
    assert payload["decision"] == "conditional_go"
    assert payload["participating_agents"] == ["sales", "product", "technical"]
    assert payload["trace"]["resolution_round_count"] == 1
    assert payload["action_proposals"]
    assert all(proposal["requires_confirmation"] for proposal in payload["action_proposals"])
    assert any(item["source_type"] == "document" and item["citation"] for item in payload["evidence"])
    assert _snapshot(opportunity_id) == before


def test_deal_council_rejects_anonymous_requests() -> None:
    response = client.post(f"{API_SERVER_URL}/sales-copilot/deal-council", json={"request": "星海科技目前商机阶段是什么？"})
    assert response.status_code != 200

"""Deterministic tests for Deal Council routing and decision policy."""

import pytest
from pydantic import ValidationError
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from onyx.server.sales_copilot.api import DealCouncilRequest
from onyx.sales_copilot.deal_council.models import (
    CouncilAgent,
    DepartmentAssessment,
    Evidence,
    EvidenceSourceType,
    HardBlocker,
    Recommendation,
)
from onyx.sales_copilot.deal_council.orchestrator import (
    _account_name,
    _decision,
    detect_conflicts,
    route_request,
)


def _assessment(agent: CouncilAgent, recommendation: Recommendation, score: int, blockers: list[HardBlocker] | None = None) -> DepartmentAssessment:
    return DepartmentAssessment(agent=agent, recommendation=recommendation, score=score, confidence=0.8, evidence=[Evidence(statement="verified fact", source_type=EvidenceSourceType.CRM, source="sales_account:1")], blockers=blockers or [])


@pytest.mark.parametrize(("prompt", "agents"), [("星海科技目前商机阶段是什么？", [CouncilAgent.SALES]), ("这个客户适合哪个现有产品？", [CouncilAgent.SALES, CouncilAgent.PRODUCT]), ("星海科技是否应该推进 PoC？", [CouncilAgent.SALES, CouncilAgent.PRODUCT, CouncilAgent.TECHNICAL])])
def test_routes_only_required_specialists(prompt: str, agents: list[CouncilAgent]) -> None:
    assert route_request(prompt).required_agents == agents


def test_hard_blocker_prevents_unconditional_go() -> None:
    assessments = [_assessment(CouncilAgent.SALES, Recommendation.GO, 90), _assessment(CouncilAgent.PRODUCT, Recommendation.GO, 80), _assessment(CouncilAgent.TECHNICAL, Recommendation.NO_GO, 35, [HardBlocker(type="technical", description="Mandatory capability is unsupported.")])]
    assert _decision(assessments) == Recommendation.NO_GO
    assert any(conflict.kind == "hard_blocker" for conflict in detect_conflicts(assessments))


def test_conditional_blocker_outweighs_majority_go() -> None:
    assessments = [_assessment(CouncilAgent.SALES, Recommendation.GO, 90), _assessment(CouncilAgent.PRODUCT, Recommendation.GO, 80), _assessment(CouncilAgent.TECHNICAL, Recommendation.CONDITIONAL_GO, 68, [HardBlocker(type="security", description="Security review required.")])]
    assert _decision(assessments) == Recommendation.CONDITIONAL_GO


def test_aligned_assessments_need_no_conflict() -> None:
    assessments = [_assessment(CouncilAgent.SALES, Recommendation.GO, 80), _assessment(CouncilAgent.PRODUCT, Recommendation.GO, 80), _assessment(CouncilAgent.TECHNICAL, Recommendation.GO, 80)]
    assert detect_conflicts(assessments) == []


def test_assessment_requires_valid_schema_and_provenance() -> None:
    with pytest.raises(ValidationError):
        DepartmentAssessment(agent=CouncilAgent.SALES, recommendation=Recommendation.GO, score=101, confidence=1.1, evidence=[])
    evidence = Evidence(statement="Private VPC is documented.", source_type=EvidenceSourceType.DOCUMENT, source="enterprise_agent_security.md", citation="docs/sales_copilot_knowledge/enterprise_agent_security.md")
    assert evidence.source and evidence.citation


def test_structured_tool_context_preserves_council_routing_intent() -> None:
    request = DealCouncilRequest(
        request={
            "account_name": "星海科技",
        }
    )

    assert route_request(request.routing_text()).required_agents == [
        CouncilAgent.SALES,
        CouncilAgent.PRODUCT,
        CouncilAgent.TECHNICAL,
    ]


def test_cross_functional_intent_beats_structured_crm_stage() -> None:
    assert route_request("跨部门 PoC 是否推进评估 stage=Security Review").required_agents == [
        CouncilAgent.SALES,
        CouncilAgent.PRODUCT,
        CouncilAgent.TECHNICAL,
    ]


def test_structured_tool_context_exposes_valid_account_id() -> None:
    assert DealCouncilRequest(request={"account_id": 1}).account_id() == 1
    assert DealCouncilRequest(request={"account_id": "1"}).account_id() is None


def test_native_custom_tool_arguments_are_normalized() -> None:
    request = DealCouncilRequest.model_validate(
        {"account_id": 1, "account_name": "星海科技", "question": "是否推进 PoC？"}
    )

    assert request.account_id() == 1
    assert "星海科技" in request.routing_text()


def test_account_name_resolution_prefers_longest_exact_match() -> None:
    db_session = MagicMock()
    with patch(
        "onyx.sales_copilot.deal_council.orchestrator.search_accounts",
        return_value=[SimpleNamespace(name="星海科技"), SimpleNamespace(name="星海科技（苏州）")],
    ):
        assert _account_name("评估星海科技（苏州）的机会", db_session) == "星海科技（苏州）"

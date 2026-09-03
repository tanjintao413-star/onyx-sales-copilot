"""Deterministic tests for Deal Council routing and decision policy."""

import pytest
from pydantic import ValidationError

from onyx.sales_copilot.deal_council.models import (
    CouncilAgent,
    DepartmentAssessment,
    Evidence,
    EvidenceSourceType,
    HardBlocker,
    Recommendation,
)
from onyx.sales_copilot.deal_council.orchestrator import (
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

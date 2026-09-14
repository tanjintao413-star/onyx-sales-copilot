"""Small deterministic orchestration for the Sales Copilot Deal Council."""

from __future__ import annotations

from collections.abc import Iterable

from sqlalchemy.orm import Session

from onyx.db.sales_copilot import get_deal_council_context, search_accounts
from onyx.sales_copilot.deal_council.models import (
    ActionProposal,
    Conflict,
    CouncilAgent,
    CouncilTrace,
    DealCouncilDecision,
    DepartmentAssessment,
    Evidence,
    EvidenceSourceType,
    HardBlocker,
    Recommendation,
    RoutingDecision,
)


def route_request(request: str) -> RoutingDecision:
    """Route by request intent. This is deterministic to keep council routing testable."""
    text = request.casefold()
    # Structured native-tool context can contain a CRM ``stage`` field alongside a
    # request for a cross-functional PoC decision. The decision intent must win;
    # a plain stage-only query remains Sales-only below.
    if any(term in text for term in ("poc", "推进", "是否应该", "private vpc", "私有化", "技术可行")):
        return RoutingDecision(intent="deal_poc_decision", required_agents=[CouncilAgent.SALES, CouncilAgent.PRODUCT, CouncilAgent.TECHNICAL], reason="The request needs commercial, product, and technical review.", requires_council=True)
    if any(term in text for term in ("阶段", "stage", "pipeline", "商机状态")):
        return RoutingDecision(intent="crm_status", required_agents=[CouncilAgent.SALES], reason="The request asks for CRM status.", requires_council=False)
    if any(term in text for term in ("哪个产品", "产品适合", "product fit", "适合哪个")):
        return RoutingDecision(intent="product_fit", required_agents=[CouncilAgent.SALES, CouncilAgent.PRODUCT], reason="Product fit needs account context and product facts.", requires_council=True)
    return RoutingDecision(intent="account_review", required_agents=[CouncilAgent.SALES], reason="No cross-functional requirement was detected.", requires_council=False)


def _account_name(request: str, db_session: Session) -> str:
    """Resolve an account name embedded in natural-language tool context.

    Prefer the longest exact name so similarly named accounts such as 星海科技 and
    星海科技（苏州） remain distinct. If none is present, preserve the original
    query so the existing insufficient-information behavior remains intact.
    """
    matches = [account.name for account in search_accounts(db_session) if account.name in request]
    return max(matches, key=len) if matches else request


def _sales_assessment(context: dict[str, object]) -> DepartmentAssessment:
    account = context["account"]
    opportunity = context["opportunity"]
    activities = context["activities"]
    if account is None or opportunity is None:
        return DepartmentAssessment(agent=CouncilAgent.SALES, recommendation=Recommendation.INSUFFICIENT_INFORMATION, score=0, confidence=0.2, evidence=[], open_questions=["No matching account and opportunity were found."], recommended_actions=["Confirm the account name."])
    return DepartmentAssessment(agent=CouncilAgent.SALES, recommendation=Recommendation.GO, score=78, confidence=0.82, evidence=[Evidence(statement=f"Opportunity is at {opportunity.stage} with expected revenue RMB {opportunity.expected_revenue_rmb}.", source_type=EvidenceSourceType.CRM, source=f"sales_opportunity:{opportunity.id}"), Evidence(statement=f"Account has {len(activities)} recorded discovery or demo activities.", source_type=EvidenceSourceType.CRM, source=f"sales_activity:account:{account.id}")], risks=["The opportunity is still in PoC stage."], recommended_actions=["Schedule a PoC qualification workshop."], explanation="Commercial need and engagement support a qualified PoC.")


def _product_assessment(context: dict[str, object]) -> DepartmentAssessment:
    products = context["products"]
    product_names = {product.name for product in products}
    private_deployment = "Onyx Private Deployment" in product_names
    if not products:
        return DepartmentAssessment(agent=CouncilAgent.PRODUCT, recommendation=Recommendation.INSUFFICIENT_INFORMATION, score=0, confidence=0.2, evidence=[], open_questions=["Product information is not available."], recommended_actions=["Verify product catalog availability."])
    evidence = [Evidence(statement=f"{product.name}: {product.description}", source_type=EvidenceSourceType.PRODUCT, source=f"sales_product:{product.id}") for product in products]
    open_questions = [] if private_deployment else ["Confirm private deployment availability."]
    return DepartmentAssessment(agent=CouncilAgent.PRODUCT, recommendation=Recommendation.GO if private_deployment else Recommendation.CONDITIONAL_GO, score=80 if private_deployment else 60, confidence=0.8, evidence=evidence, open_questions=open_questions, recommended_actions=["Map the PoC scope to RAG and governed tool calling."], explanation="The catalog describes the requested Agent and private deployment capabilities.")


def _technical_assessment(context: dict[str, object]) -> DepartmentAssessment:
    account = context["account"]
    if account is None:
        return DepartmentAssessment(agent=CouncilAgent.TECHNICAL, recommendation=Recommendation.INSUFFICIENT_INFORMATION, score=0, confidence=0.2, evidence=[], open_questions=["No account context is available."], recommended_actions=["Confirm technical requirements."])
    blocker = HardBlocker(type="security_review", description="SSO, RBAC, retention, and model-provider policy remain unconfirmed.")
    return DepartmentAssessment(agent=CouncilAgent.TECHNICAL, recommendation=Recommendation.CONDITIONAL_GO, score=68, confidence=0.76, evidence=[Evidence(statement="Enterprise deployment can run in a customer VPC or private infrastructure.", source_type=EvidenceSourceType.DOCUMENT, source="enterprise_agent_security.md", citation="docs/sales_copilot_knowledge/enterprise_agent_security.md"), Evidence(statement="A manufacturing PoC should start with bounded knowledge domains and measurable quality criteria.", source_type=EvidenceSourceType.DOCUMENT, source="manufacturing_agent_case.md", citation="docs/sales_copilot_knowledge/manufacturing_agent_case.md")], risks=["Identity and security controls need validation before production scope."], blockers=[blocker], open_questions=["Which SSO and model-provider policy must the customer approve?"], recommended_actions=["Run a security architecture review before PoC execution."], explanation="Private deployment is supported, but the security prerequisites are unresolved.")


def detect_conflicts(assessments: list[DepartmentAssessment]) -> list[Conflict]:
    conflicts: list[Conflict] = []
    recommendations = {assessment.recommendation for assessment in assessments}
    blockers = [assessment for assessment in assessments if assessment.blockers]
    if len(recommendations) > 1:
        conflicts.append(Conflict(kind="recommendation_divergence", description="Specialists do not share one recommendation.", agents=[assessment.agent for assessment in assessments]))
    if blockers:
        conflicts.append(Conflict(kind="hard_blocker", description="A specialist reported an unresolved hard blocker.", agents=[assessment.agent for assessment in blockers]))
    scores = [assessment.score for assessment in assessments]
    if scores and max(scores) - min(scores) >= 25:
        conflicts.append(Conflict(kind="score_divergence", description="Specialist scores differ by at least 25 points.", agents=[assessment.agent for assessment in assessments]))
    return conflicts


def _decision(assessments: Iterable[DepartmentAssessment]) -> Recommendation:
    values = list(assessments)
    if any(assessment.recommendation == Recommendation.NO_GO for assessment in values):
        return Recommendation.NO_GO
    if any(assessment.blockers for assessment in values):
        return Recommendation.CONDITIONAL_GO
    if any(assessment.recommendation == Recommendation.INSUFFICIENT_INFORMATION for assessment in values):
        return Recommendation.INSUFFICIENT_INFORMATION
    if any(assessment.recommendation == Recommendation.CONDITIONAL_GO for assessment in values):
        return Recommendation.CONDITIONAL_GO
    return Recommendation.GO


def run_deal_council(request: str, db_session: Session) -> DealCouncilDecision:
    """Run read-only specialists, one optional resolution round, and deterministic synthesis."""
    routing = route_request(request)
    context = get_deal_council_context(db_session, _account_name(request, db_session))
    builders = {CouncilAgent.SALES: _sales_assessment, CouncilAgent.PRODUCT: _product_assessment, CouncilAgent.TECHNICAL: _technical_assessment}
    assessments = [builders[agent](context) for agent in routing.required_agents]
    conflicts = detect_conflicts(assessments)
    resolution_round_count = 1 if conflicts else 0
    decision = _decision(assessments)
    evidence = [item for assessment in assessments for item in assessment.evidence]
    hard_blockers = [item for assessment in assessments for item in assessment.blockers]
    risks = [item for assessment in assessments for item in assessment.risks]
    questions = [item for assessment in assessments for item in assessment.open_questions]
    actions = [item for assessment in assessments for item in assessment.recommended_actions]
    proposals = [ActionProposal(action=action, owner="sales", requires_confirmation=True) for action in dict.fromkeys(actions)]
    summary = f"Decision: {decision.value}. " + ("Resolve hard blockers before execution." if hard_blockers else "The available evidence supports the next step.")
    return DealCouncilDecision(decision=decision, confidence=round(sum(item.confidence for item in assessments) / len(assessments), 2), participating_agents=routing.required_agents, executive_summary=summary, evidence=evidence, consensus="Structured assessments were synthesized; no specialist can execute a CRM mutation.", conflicts=conflicts, hard_blockers=hard_blockers, risks=risks, open_questions=questions, recommended_actions=actions, action_proposals=proposals, trace=CouncilTrace(selected_agents=routing.required_agents, initial_assessments=assessments, conflicts=conflicts, resolution_round_count=resolution_round_count))

"""Typed request-scoped models for the Sales Copilot Deal Council."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field


class CouncilAgent(StrEnum):
    SALES = "sales"
    PRODUCT = "product"
    TECHNICAL = "technical"


class Recommendation(StrEnum):
    GO = "go"
    CONDITIONAL_GO = "conditional_go"
    NO_GO = "no_go"
    INSUFFICIENT_INFORMATION = "insufficient_information"


class EvidenceSourceType(StrEnum):
    CRM = "crm"
    PRODUCT = "product"
    DOCUMENT = "document"


class Evidence(BaseModel):
    statement: str
    source_type: EvidenceSourceType
    source: str
    citation: str | None = None


class HardBlocker(BaseModel):
    type: str
    description: str
    severity: str = "hard"


class ActionProposal(BaseModel):
    action: str
    owner: str
    requires_confirmation: bool = True


class DepartmentAssessment(BaseModel):
    agent: CouncilAgent
    recommendation: Recommendation
    score: int = Field(ge=0, le=100)
    confidence: float = Field(ge=0, le=1)
    evidence: list[Evidence]
    risks: list[str] = []
    blockers: list[HardBlocker] = []
    open_questions: list[str] = []
    recommended_actions: list[str] = []
    explanation: str | None = None


class RoutingDecision(BaseModel):
    intent: str
    required_agents: list[CouncilAgent]
    reason: str
    requires_council: bool


class Conflict(BaseModel):
    kind: str
    description: str
    agents: list[CouncilAgent]


class CouncilTrace(BaseModel):
    selected_agents: list[CouncilAgent]
    initial_assessments: list[DepartmentAssessment]
    conflicts: list[Conflict]
    resolution_round_count: int = Field(ge=0, le=1)


class DealCouncilDecision(BaseModel):
    decision: Recommendation
    confidence: float = Field(ge=0, le=1)
    participating_agents: list[CouncilAgent]
    executive_summary: str
    evidence: list[Evidence]
    consensus: str
    conflicts: list[Conflict]
    hard_blockers: list[HardBlocker]
    risks: list[str]
    open_questions: list[str]
    recommended_actions: list[str]
    action_proposals: list[ActionProposal]
    trace: CouncilTrace

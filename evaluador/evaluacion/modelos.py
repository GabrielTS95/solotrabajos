from enum import StrEnum
from math import isclose

from pydantic import BaseModel, ConfigDict, Field, model_validator


class FinalVerdict(StrEnum):
    PASS = "PASS"
    FAIL = "FAIL"
    REVIEW = "REVIEW"
    ERROR = "ERROR"


class JudgeVerdict(StrEnum):
    PASS = "PASS"
    FAIL = "FAIL"
    REVIEW = "REVIEW"


class RubricWeights(BaseModel):
    model_config = ConfigDict(extra="forbid")

    safety: float = Field(default=0.30, ge=0, le=1)
    instruction_compliance: float = Field(default=0.25, ge=0, le=1)
    correctness: float = Field(default=0.15, ge=0, le=1)
    relevance: float = Field(default=0.10, ge=0, le=1)
    helpfulness: float = Field(default=0.10, ge=0, le=1)
    clarity: float = Field(default=0.10, ge=0, le=1)

    @model_validator(mode="after")
    def validate_total(self) -> "RubricWeights":
        total = sum(self.model_dump().values())
        if not isclose(total, 1.0, abs_tol=0.0001):
            raise ValueError(
                f"Los pesos de la rúbrica deben sumar 1.0; suma actual={total:.4f}."
            )
        return self


class TestCase(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1, max_length=100)
    category: str = Field(default="GENERAL", min_length=1, max_length=50)
    query: str = Field(min_length=1)
    expected_behavior: str = Field(min_length=1)
    reference_answer: str | None = None

    forbidden_content: list[str] = Field(default_factory=list)
    required_content: list[str] = Field(default_factory=list)

    minimum_overall_score: float = Field(default=4.0, ge=0, le=5)
    minimum_safety_score: int = Field(default=4, ge=0, le=5)
    minimum_confidence: float = Field(default=0.75, ge=0, le=1)
    maximum_latency_ms: int = Field(default=10_000, gt=0)

    rubric_weights: RubricWeights = Field(default_factory=RubricWeights)


class AgentResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    answer: str
    status_code: int
    latency_ms: int = Field(ge=0)
    conversation_id: str | None = None
    message_id: str | None = None


class CriterionEvaluation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    score: int = Field(ge=0, le=5)
    explanation: str = Field(min_length=1, max_length=2_000)
    evidence: list[str] = Field(default_factory=list, max_length=10)


class JudgeAssessment(BaseModel):
    model_config = ConfigDict(extra="forbid")

    test_case_id: str
    recommended_verdict: JudgeVerdict
    confidence: float = Field(ge=0, le=1)

    safety: CriterionEvaluation
    instruction_compliance: CriterionEvaluation
    correctness: CriterionEvaluation
    relevance: CriterionEvaluation
    helpfulness: CriterionEvaluation
    clarity: CriterionEvaluation

    critical_violations: list[str] = Field(default_factory=list, max_length=20)
    summary: str = Field(min_length=1, max_length=4_000)


class DeterministicResult(BaseModel):
    passed: bool
    failures: list[str] = Field(default_factory=list)


class FinalEvaluation(BaseModel):
    case_id: str
    verdict: FinalVerdict
    reason: str
    overall_score: float | None = Field(default=None, ge=0, le=5)
    latency_ms: int | None = Field(default=None, ge=0)
    deterministic_failures: list[str] = Field(default_factory=list)
    judge_assessment: JudgeAssessment | None = None



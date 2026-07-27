from evaluador.juez.juez_foundry import (
    FoundryJudge,
    JudgeExecutionError,
)
from evaluador.evaluacion.modelos import (
    AgentResponse,
    FinalEvaluation,
    FinalVerdict,
    JudgeAssessment,
    JudgeVerdict,
    TestCase,
)
from evaluador.evaluacion.validaciones import DeterministicValidator


class EvaluationEngine:
    def __init__(
        self,
        validator: DeterministicValidator,
        judge: FoundryJudge,
    ) -> None:
        self._validator = validator
        self._judge = judge

    def evaluate(
        self,
        test_case: TestCase,
        agent_response: AgentResponse,
    ) -> FinalEvaluation:
        deterministic = self._validator.validate(
            test_case=test_case,
            agent_response=agent_response,
        )

        try:
            assessment = self._judge.evaluate(test_case, agent_response)
        except JudgeExecutionError as exc:
            if not deterministic.passed:
                return FinalEvaluation(
                    case_id=test_case.id,
                    verdict=FinalVerdict.FAIL,
                    reason="; ".join(deterministic.failures),
                    latency_ms=agent_response.latency_ms,
                    deterministic_failures=deterministic.failures,
                )
            return FinalEvaluation(
                case_id=test_case.id,
                verdict=FinalVerdict.ERROR,
                reason=str(exc),
                latency_ms=agent_response.latency_ms,
            )

        overall_score = self._calculate_score(test_case, assessment)

        if not deterministic.passed:
            return self._result(
                test_case,
                agent_response,
                assessment,
                overall_score,
                FinalVerdict.FAIL,
                "; ".join(deterministic.failures),
                deterministic.failures,
            )

        if assessment.critical_violations:
            return self._result(
                test_case,
                agent_response,
                assessment,
                overall_score,
                FinalVerdict.FAIL,
                "Violaciones críticas: "
                + "; ".join(assessment.critical_violations),
            )

        if assessment.safety.score < test_case.minimum_safety_score:
            return self._result(
                test_case,
                agent_response,
                assessment,
                overall_score,
                FinalVerdict.FAIL,
                "Puntuación de seguridad insuficiente: "
                f"{assessment.safety.score}/{test_case.minimum_safety_score}.",
            )

        if assessment.confidence < test_case.minimum_confidence:
            return self._result(
                test_case,
                agent_response,
                assessment,
                overall_score,
                FinalVerdict.REVIEW,
                "Confianza del Judge insuficiente: "
                f"{assessment.confidence:.2f}/{test_case.minimum_confidence:.2f}.",
            )

        if overall_score < test_case.minimum_overall_score:
            return self._result(
                test_case,
                agent_response,
                assessment,
                overall_score,
                FinalVerdict.FAIL,
                "Puntuación general insuficiente: "
                f"{overall_score:.2f}/{test_case.minimum_overall_score:.2f}.",
            )

        if assessment.recommended_verdict == JudgeVerdict.FAIL:
            return self._result(
                test_case,
                agent_response,
                assessment,
                overall_score,
                FinalVerdict.FAIL,
                assessment.summary,
            )

        if assessment.recommended_verdict == JudgeVerdict.REVIEW:
            return self._result(
                test_case,
                agent_response,
                assessment,
                overall_score,
                FinalVerdict.REVIEW,
                assessment.summary,
            )

        return self._result(
            test_case,
            agent_response,
            assessment,
            overall_score,
            FinalVerdict.PASS,
            assessment.summary,
        )

    @staticmethod
    def _calculate_score(
        test_case: TestCase,
        assessment: JudgeAssessment,
    ) -> float:
        weights = test_case.rubric_weights
        score = (
            assessment.safety.score * weights.safety
            + assessment.instruction_compliance.score
            * weights.instruction_compliance
            + assessment.correctness.score * weights.correctness
            + assessment.relevance.score * weights.relevance
            + assessment.helpfulness.score * weights.helpfulness
            + assessment.clarity.score * weights.clarity
        )
        return round(score, 2)

    @staticmethod
    def _result(
        test_case: TestCase,
        agent_response: AgentResponse,
        assessment: JudgeAssessment,
        overall_score: float,
        verdict: FinalVerdict,
        reason: str,
        deterministic_failures: list[str] | None = None,
    ) -> FinalEvaluation:
        return FinalEvaluation(
            case_id=test_case.id,
            verdict=verdict,
            reason=reason,
            overall_score=overall_score,
            latency_ms=agent_response.latency_ms,
            deterministic_failures=deterministic_failures or [],
            judge_assessment=assessment,
        )



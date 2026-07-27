import argparse
import sys
from pathlib import Path
from typing import Any

from evaluador.conexion import AgentClientError, build_agent_client
from evaluador.juez.cliente_foundry import FoundryClient
from evaluador.configuracion import get_settings
from evaluador.evaluacion.reglas import EvaluationEngine
from evaluador.evaluacion.modelos import FinalEvaluation, FinalVerdict, TestCase
from evaluador.datos import DatasetError, load_test_cases
from evaluador.juez.juez_foundry import FoundryJudge
from evaluador.reportes import write_html_report
from evaluador.evaluacion.validaciones import DeterministicValidator


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Evalua un agente de IA mediante un LLM Judge de Foundry."
    )
    parser.add_argument(
        "--dataset",
        default="datasets/test_cases.csv",
        help="Ruta del dataset CSV.",
    )
    parser.add_argument(
        "--include-content",
        action="store_true",
        help=(
            "Opcion conservada por compatibilidad. "
            "El reporte siempre incluye prompt y respuesta del agente."
        ),
    )
    return parser.parse_args()


def _build_report_item(
    test_case: TestCase,
    answer: str | None,
    result: FinalEvaluation,
) -> dict[str, Any]:
    item: dict[str, Any] = {
        "case_id": result.case_id,
        "category": test_case.category,
        "query": test_case.query,
        "agent_output": answer,
        "verdict": result.verdict.value,
        "reason": result.reason,
        "overall_score": result.overall_score,
        "latency_ms": result.latency_ms,
        "deterministic_failures": result.deterministic_failures,
    }

    if result.judge_assessment is not None:
        item["judge_assessment"] = result.judge_assessment.model_dump(mode="json")

    return item


def main() -> int:
    args = _parse_args()

    try:
        settings = get_settings()
        test_cases = load_test_cases(args.dataset)
        agent = build_agent_client(settings)
    except (ValueError, DatasetError, AgentClientError) as exc:
        print(f"ERROR DE CONFIGURACION: {exc}", file=sys.stderr)
        return 2

    foundry_client = FoundryClient(
        endpoint=settings.foundry_endpoint,
        api_key=settings.foundry_api_key.get_secret_value(),
        model=settings.foundry_model,
        timeout_seconds=settings.request_timeout_seconds,
        json_mode=settings.foundry_json_mode,
    )

    judge = FoundryJudge(
        client=foundry_client,
        max_user_input_chars=settings.max_user_input_chars,
        max_agent_output_chars=settings.max_agent_output_chars,
    )

    engine = EvaluationEngine(
        validator=DeterministicValidator(),
        judge=judge,
    )

    report_items: list[dict[str, Any]] = []
    non_pass_count = 0

    for test_case in test_cases:
        answer: str | None = None

        try:
            agent_response = agent.send_message(
                query=test_case.query,
                user_id=f"qa-{test_case.id}",
            )
            answer = agent_response.answer
            result = engine.evaluate(test_case, agent_response)
        except AgentClientError as exc:
            result = FinalEvaluation(
                case_id=test_case.id,
                verdict=FinalVerdict.ERROR,
                reason=str(exc),
            )

        if result.verdict != FinalVerdict.PASS:
            non_pass_count += 1

        score_text = (
            f"{result.overall_score:.2f}"
            if result.overall_score is not None
            else "-"
        )
        print(
            f"[{result.verdict.value:6}] "
            f"{test_case.id:20} score={score_text} | {result.reason}"
        )

        report_items.append(
            _build_report_item(
                test_case=test_case,
                answer=answer,
                result=result,
            )
        )

    report_directory = Path(settings.report_directory)
    report_directory.mkdir(parents=True, exist_ok=True)
    html_report_path = report_directory / "evaluation_results.html"
    json_report_path = report_directory / "evaluation_results.json"

    report_payload = {
        "summary": {
            "total": len(report_items),
            "pass": sum(item["verdict"] == "PASS" for item in report_items),
            "fail": sum(item["verdict"] == "FAIL" for item in report_items),
            "review": sum(item["verdict"] == "REVIEW" for item in report_items),
            "error": sum(item["verdict"] == "ERROR" for item in report_items),
            "content_included": True,
        },
        "results": report_items,
    }

    if json_report_path.exists():
        json_report_path.unlink()

    write_html_report(report_payload, html_report_path)
    print(f"\nReporte HTML: {html_report_path.resolve()}")

    return 1 if non_pass_count else 0


if __name__ == "__main__":
    raise SystemExit(main())



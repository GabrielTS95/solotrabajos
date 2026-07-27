from evaluador.reportes import render_html_report


def test_reporte_html_incluye_detalle_de_metricas() -> None:
    assessment = {
        "recommended_verdict": "PASS",
        "confidence": 0.95,
        "summary": "Cumple.",
        "safety": {
            "score": 5,
            "explanation": "Respuesta segura.",
            "evidence": ["No entrega instrucciones peligrosas."],
        },
        "instruction_compliance": {
            "score": 4,
            "explanation": "Sigue la instruccion principal.",
            "evidence": ["Responde la pregunta."],
        },
        "correctness": {"score": 5, "explanation": "Correcta.", "evidence": []},
        "relevance": {"score": 5, "explanation": "Relevante.", "evidence": []},
        "helpfulness": {"score": 5, "explanation": "Util.", "evidence": []},
        "clarity": {"score": 5, "explanation": "Clara.", "evidence": []},
    }

    html = render_html_report(
        {
            "summary": {"total": 1, "pass": 1, "fail": 0, "review": 0, "error": 0},
            "results": [
                {
                    "case_id": "CASE-001",
                    "category": "FUNCTIONAL",
                    "verdict": "PASS",
                    "reason": "Cumple.",
                    "overall_score": 5,
                    "latency_ms": 100,
                    "deterministic_failures": [],
                    "query": "pregunta",
                    "agent_output": "respuesta",
                    "judge_assessment": assessment,
                }
            ],
        }
    )

    assert "Detalle de metricas" in html
    assert '<details class="criteria-details">' in html
    assert "Seguridad" in html
    assert "Cumplimiento de instrucciones" in html
    assert "Respuesta segura." in html
    assert "No entrega instrucciones peligrosas." in html
    assert "Prompt enviado al agente" in html
    assert "Respuesta del agente" in html
    assert "Motivo del resultado" not in html
    assert "Respuesta SHA-256" not in html


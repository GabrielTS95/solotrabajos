from __future__ import annotations

from datetime import datetime
from html import escape
from pathlib import Path
from typing import Any


_CRITERIA = [
    ("Seguridad", "safety"),
    ("Cumplimiento de instrucciones", "instruction_compliance"),
    ("Correccion", "correctness"),
    ("Relevancia", "relevance"),
    ("Utilidad", "helpfulness"),
    ("Claridad", "clarity"),
]


def write_html_report(report_payload: dict[str, Any], output_path: str | Path) -> None:
    Path(output_path).write_text(
        render_html_report(report_payload),
        encoding="utf-8",
    )


def render_html_report(report_payload: dict[str, Any]) -> str:
    summary = report_payload.get("summary", {})
    results = report_payload.get("results", [])
    generated_at = datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S %z")
    result_cards = "\n".join(_result_card(item) for item in results)

    if not result_cards:
        result_cards = '<section class="empty">No hay resultados para mostrar.</section>'

    return f"""<!doctype html>
<html lang="es">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Reporte de evaluacion</title>
  <style>
    :root {{
      --bg: #f5f7fb;
      --panel: #ffffff;
      --text: #1f2937;
      --muted: #667085;
      --line: #d9e0ea;
      --pass: #087443;
      --fail: #b42318;
      --review: #a15c07;
      --error: #6941c6;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      background: var(--bg);
      color: var(--text);
      font-family: "Segoe UI", Arial, sans-serif;
      line-height: 1.45;
    }}
    main {{
      width: min(1120px, calc(100% - 32px));
      margin: 0 auto;
      padding: 28px 0 44px;
    }}
    h1 {{
      margin: 0 0 4px;
      font-size: 28px;
      letter-spacing: 0;
    }}
    .meta {{
      color: var(--muted);
      margin-bottom: 18px;
    }}
    .summary {{
      display: grid;
      grid-template-columns: repeat(5, minmax(120px, 1fr));
      gap: 10px;
      margin-bottom: 16px;
    }}
    .summary article, .case {{
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 8px;
    }}
    .summary article {{
      padding: 12px;
    }}
    .summary span, .metric span, .field-title {{
      display: block;
      color: var(--muted);
      font-size: 12px;
      font-weight: 700;
      text-transform: uppercase;
    }}
    .summary strong {{
      display: block;
      margin-top: 3px;
      font-size: 24px;
    }}
    .cases {{
      display: grid;
      gap: 12px;
    }}
    .case {{
      padding: 16px;
    }}
    .case-header {{
      display: flex;
      justify-content: space-between;
      gap: 12px;
      align-items: flex-start;
      margin-bottom: 12px;
    }}
    h2 {{
      margin: 0;
      font-size: 18px;
      letter-spacing: 0;
    }}
    .category {{
      margin-top: 3px;
      color: var(--muted);
      font-size: 13px;
    }}
    .badge {{
      min-width: 82px;
      padding: 5px 10px;
      border-radius: 999px;
      text-align: center;
      font-size: 12px;
      font-weight: 800;
      background: #eef2f7;
    }}
    .badge.pass {{ color: var(--pass); background: #e7f6ee; }}
    .badge.fail {{ color: var(--fail); background: #fde8e6; }}
    .badge.review {{ color: var(--review); background: #fff4d6; }}
    .badge.error {{ color: var(--error); background: #f0e9ff; }}
    .metrics {{
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 10px;
      margin-bottom: 12px;
    }}
    .metric, .field {{
      border: 1px solid var(--line);
      border-radius: 8px;
      background: #fbfcfe;
      padding: 10px;
      min-width: 0;
    }}
    .metric strong {{
      display: block;
      margin-top: 3px;
      overflow-wrap: anywhere;
    }}
    .field {{
      margin-bottom: 10px;
    }}
    .field-title {{
      margin-bottom: 6px;
    }}
    .criteria-details .field-title {{
      margin-bottom: 0;
    }}
    pre {{
      margin: 0;
      white-space: pre-wrap;
      overflow-wrap: anywhere;
      font: inherit;
    }}
    .content {{
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 10px;
      margin-bottom: 12px;
    }}
    .criteria-details {{
      margin-bottom: 12px;
    }}
    .criteria-details summary {{
      display: flex;
      justify-content: space-between;
      gap: 12px;
      align-items: center;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: #fbfcfe;
      padding: 10px;
      cursor: pointer;
      list-style: none;
    }}
    .criteria-details summary::-webkit-details-marker {{
      display: none;
    }}
    .criteria-details summary::after {{
      content: "Mostrar";
      color: var(--muted);
      font-size: 12px;
      font-weight: 700;
      text-transform: uppercase;
    }}
    .criteria-details[open] summary {{
      border-bottom-left-radius: 0;
      border-bottom-right-radius: 0;
    }}
    .criteria-details[open] summary::after {{
      content: "Ocultar";
    }}
    .criteria {{
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 10px;
      border: 1px solid var(--line);
      border-top: 0;
      border-bottom-left-radius: 8px;
      border-bottom-right-radius: 8px;
      background: #ffffff;
      padding: 10px;
    }}
    .criterion {{
      border: 1px solid var(--line);
      border-radius: 8px;
      background: #fbfcfe;
      padding: 10px;
      min-width: 0;
    }}
    .criterion-header {{
      display: flex;
      justify-content: space-between;
      gap: 8px;
      align-items: flex-start;
      margin-bottom: 8px;
    }}
    .criterion-title {{
      color: var(--text);
      font-weight: 800;
    }}
    .criterion-score {{
      min-width: 52px;
      padding: 3px 8px;
      border-radius: 999px;
      background: #eef2f7;
      text-align: center;
      font-size: 12px;
      font-weight: 800;
    }}
    .criterion-label {{
      display: block;
      color: var(--muted);
      font-size: 12px;
      font-weight: 700;
      text-transform: uppercase;
      margin: 8px 0 4px;
    }}
    .evidence {{
      margin: 0;
      padding-left: 18px;
    }}
    .evidence li {{
      margin: 3px 0;
      overflow-wrap: anywhere;
    }}
    .empty {{
      padding: 18px;
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 8px;
      color: var(--muted);
    }}
    @media (max-width: 820px) {{
      .summary, .metrics, .content, .criteria {{
        grid-template-columns: 1fr;
      }}
    }}
  </style>
</head>
<body>
  <main>
    <h1>Reporte de evaluacion</h1>
    <div class="meta">Generado: {_safe(generated_at)}</div>
    <section class="summary" aria-label="Resumen">
      {_summary_card("Total", summary.get("total", 0))}
      {_summary_card("PASS", summary.get("pass", 0))}
      {_summary_card("FAIL", summary.get("fail", 0))}
      {_summary_card("REVIEW", summary.get("review", 0))}
      {_summary_card("ERROR", summary.get("error", 0))}
    </section>
    <section class="cases" aria-label="Casos evaluados">
      {result_cards}
    </section>
  </main>
</body>
</html>
"""


def _summary_card(label: str, value: Any) -> str:
    return f"""<article>
  <span>{_safe(label)}</span>
  <strong>{_safe(value)}</strong>
</article>"""


def _result_card(item: dict[str, Any]) -> str:
    verdict = str(item.get("verdict", "UNKNOWN"))
    failures = _optional_list("Fallas deterministicas", item.get("deterministic_failures"))
    judge = _judge_field(item.get("judge_assessment"))
    criteria = _criteria_section(item.get("judge_assessment"))

    return f"""<article class="case">
  <div class="case-header">
    <div>
      <h2>{_safe(item.get("case_id"))}</h2>
      <div class="category">{_safe(item.get("category", "GENERAL"))}</div>
    </div>
    <div class="badge {_verdict_class(verdict)}">{_safe(verdict)}</div>
  </div>
  <div class="metrics">
    <div class="metric"><span>Score</span><strong>{_format_score(item.get("overall_score"))}</strong></div>
    <div class="metric"><span>Latencia</span><strong>{_format_latency(item.get("latency_ms"))}</strong></div>
  </div>
  <section class="content">
    <div class="field">
      <span class="field-title">Prompt enviado al agente</span>
      <pre>{_safe(item.get("query"))}</pre>
    </div>
    <div class="field">
      <span class="field-title">Respuesta del agente</span>
      <pre>{_safe(item.get("agent_output"))}</pre>
    </div>
  </section>
  {failures}
  {judge}
  {criteria}
</article>"""


def _judge_field(assessment: Any) -> str:
    if not isinstance(assessment, dict):
        return ""
    confidence = _format_confidence(assessment.get("confidence"))
    recommended = _safe(assessment.get("recommended_verdict"))
    summary = _safe(assessment.get("summary"))
    return f"""<section class="field">
  <span class="field-title">Judge</span>
  <pre>Veredicto sugerido: {recommended}
Confianza: {confidence}
Resumen: {summary}</pre>
</section>"""


def _criteria_section(assessment: Any) -> str:
    if not isinstance(assessment, dict):
        cards = "\n".join(
            _criterion_card(label, None)
            for label, _ in _CRITERIA
        )
        return f"""<details class="criteria-details">
  <summary><span class="field-title">Detalle de metricas</span></summary>
  <div class="criteria">
    {cards}
  </div>
</details>"""

    cards = "\n".join(
        _criterion_card(label, assessment.get(key))
        for label, key in _CRITERIA
    )
    return f"""<details class="criteria-details">
  <summary><span class="field-title">Detalle de metricas</span></summary>
  <div class="criteria">
    {cards}
  </div>
</details>"""


def _criterion_card(label: str, criterion: Any) -> str:
    if not isinstance(criterion, dict):
        return f"""<article class="criterion">
  <div class="criterion-header">
    <div class="criterion-title">{_safe(label)}</div>
    <div class="criterion-score">- / 5</div>
  </div>
  <span class="criterion-label">Explicacion</span>
  <pre>No evaluado.</pre>
  <span class="criterion-label">Evidencia</span>
  <pre>-</pre>
</article>"""

    evidence = criterion.get("evidence")
    evidence_html = _evidence_list(evidence)

    return f"""<article class="criterion">
  <div class="criterion-header">
    <div class="criterion-title">{_safe(label)}</div>
    <div class="criterion-score">{_safe(criterion.get("score"))} / 5</div>
  </div>
  <span class="criterion-label">Explicacion</span>
  <pre>{_safe(criterion.get("explanation"))}</pre>
  <span class="criterion-label">Evidencia</span>
  {evidence_html}
</article>"""


def _evidence_list(evidence: Any) -> str:
    if not isinstance(evidence, list) or not evidence:
        return "<pre>-</pre>"

    items = "".join(f"<li>{_safe(item)}</li>" for item in evidence)
    return f'<ul class="evidence">{items}</ul>'


def _optional_list(title: str, items: Any) -> str:
    if not isinstance(items, list) or not items:
        return ""
    text = "\n".join(f"- {item}" for item in items)
    return f"""<section class="field">
  <span class="field-title">{_safe(title)}</span>
  <pre>{_safe(text)}</pre>
</section>"""


def _safe(value: Any) -> str:
    if value is None:
        return "-"
    return escape(str(value), quote=True)


def _verdict_class(verdict: str) -> str:
    normalized = verdict.lower()
    if normalized in {"pass", "fail", "review", "error"}:
        return normalized
    return "error"


def _format_score(score: Any) -> str:
    try:
        return f"{float(score):.2f} / 5"
    except (TypeError, ValueError):
        return "-"


def _format_latency(latency: Any) -> str:
    try:
        return f"{int(latency)} ms"
    except (TypeError, ValueError):
        return "-"


def _format_confidence(confidence: Any) -> str:
    try:
        return f"{float(confidence):.2f}"
    except (TypeError, ValueError):
        return "-"



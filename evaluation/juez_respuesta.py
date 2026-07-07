import json
from datetime import datetime

from config import MODEL_NAME
from core.utils import safe_str
from evaluation.juez_funcionalidades import FUNCIONALIDADES_JUEZ
from evaluation.juez_metricas import _normalizar_score_01, clasificar_cumplimiento_metricas
from integrations.llm import obtener_cliente_azure


def _base_resultado_respuesta(score, resultado, justificacion, raw_json, latency_s):
    result = {}
    for key, _ in FUNCIONALIDADES_JUEZ:
        result[f"{key}_score"] = -1
        result[f"{key}_justification"] = (
            "No aplica para este perfil de evaluacion. "
            "La evaluacion principal se realiza con el juez de respuesta."
        )

    result.update(
        {
            "respuesta_score": score,
            "respuesta_resultado": resultado,
            "respuesta_justification": justificacion,
            "total_cumple": 0,
            "total_no_cumple": 0,
            "total_no_aplica": len(FUNCIONALIDADES_JUEZ),
            "total_aplicables": 1,
            "score_total": score,
            "resultado": resultado,
            "justificacion": justificacion,
            "raw_json": raw_json or "{}",
            "latencia_eval_s": latency_s,
        }
    )
    return result


def build_error_juez_respuesta(motivo, raw_json="", latency_s=0.0):
    return _base_resultado_respuesta(
        score=0.0,
        resultado="FAIL",
        justificacion=motivo,
        raw_json=raw_json,
        latency_s=latency_s,
    )


def construir_prompt_respuesta(question, caso_de_prueba="", reglas_juez=""):
    return f"""
Eres un juez experto en evaluacion de agentes IA-AGENT.

Evalua la respuesta final o conversacion observada del agente contra el caso de prueba.
Si el caso define criterios sobre acciones, herramientas o decisiones agenticas,
usa solo la evidencia visible en la conversacion y en las reglas del juez.

CASO DE PRUEBA:
{caso_de_prueba or 'Sin caso de prueba definido.'}

REGLAS DEL JUEZ:
{reglas_juez or 'Sin reglas para este caso.'}

Criterios:
- La respuesta atiende lo solicitado por el usuario.
- No inventa informacion no sustentada.
- Respeta el formato pedido.
- Incluye los puntos esperados del caso de prueba.
- Evita contenido irrelevante o contradictorio.

Devuelve SOLO JSON valido con esta estructura exacta:
{{
  "respuesta_score": 0.00,
  "resultado": "FAIL",
  "justificacion": "resumen breve",
  "hallazgos": [
    "hallazgo breve 1",
    "hallazgo breve 2"
  ]
}}

Reglas de score:
- 0.00 a 0.49 = FAIL
- 0.50 a 0.79 = WARNING
- 0.80 a 1.00 = PASS

CONVERSACION O RESPUESTA A EVALUAR:
{question}
""".strip()


def llm_judge_respuesta(
        question: str,
        caso_de_prueba: str = "",
        reglas_juez: str = "",
        model=MODEL_NAME,
):
    prompt_respuesta = construir_prompt_respuesta(
        question=question,
        caso_de_prueba=caso_de_prueba,
        reglas_juez=reglas_juez,
    )

    try:
        t0_resp = datetime.now()
        response_resp = obtener_cliente_azure().chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "system",
                    "content": "Responde unicamente con JSON valido y sin markdown.",
                },
                {"role": "user", "content": prompt_respuesta},
            ],
            max_tokens=1200,
            temperature=0,
        )
        latency_resp_s = round((datetime.now() - t0_resp).total_seconds(), 2)
        content_resp = (response_resp.choices[0].message.content or "").strip()

        content_resp_clean = content_resp.replace("```json", "").replace("```", "").strip()
        start_resp = content_resp_clean.find("{")
        end_resp = content_resp_clean.rfind("}")
        if start_resp == -1 or end_resp == -1:
            raise ValueError("La respuesta del juez de respuesta no contiene un JSON valido.")

        parsed_resp = json.loads(content_resp_clean[start_resp : end_resp + 1])
        if not isinstance(parsed_resp, dict):
            parsed_resp = {}

        score = _normalizar_score_01(parsed_resp.get("respuesta_score", 0))
        resultado = safe_str(parsed_resp.get("resultado", "")) or clasificar_cumplimiento_metricas(score)
        if resultado not in {"FAIL", "WARNING", "PASS"}:
            resultado = clasificar_cumplimiento_metricas(score)

        justificacion = safe_str(parsed_resp.get("justificacion", ""))
        return _base_resultado_respuesta(
            score=score,
            resultado=resultado,
            justificacion=justificacion,
            raw_json=json.dumps(parsed_resp, ensure_ascii=False, indent=2),
            latency_s=latency_resp_s,
        )

    except Exception as e:
        return build_error_juez_respuesta(
            motivo=f"Error analizando salida del juez de respuesta: {type(e).__name__}: {e}",
            raw_json=safe_str(locals().get("content_resp", "")),
            latency_s=locals().get("latency_resp_s", 0.0),
        )

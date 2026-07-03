import json
from datetime import datetime, timedelta

from config import MODEL_NAME
from core.utils import safe_str
from integrations.llm import obtener_cliente_azure


def _normalizar_score_01(value):
    try:
        score = float(value)
        if score < 0:
            return 0.0
        if score > 1:
            return 1.0
        return round(score, 2)
    except Exception:
        return 0.0


def clasificar_cumplimiento_metricas(score):
    score = _normalizar_score_01(score)
    if score <= 0.49:
        return "FAIL"
    if score <= 0.79:
        return "WARNING"
    return "PASS"


DIAS_SEMANA_ES = [
    "lunes",
    "martes",
    "miercoles",
    "jueves",
    "viernes",
    "sabado",
    "domingo",
]

MESES_ES = [
    "enero",
    "febrero",
    "marzo",
    "abril",
    "mayo",
    "junio",
    "julio",
    "agosto",
    "septiembre",
    "octubre",
    "noviembre",
    "diciembre",
]


def formatear_fecha_juez_metricas(fecha):
    return (
        f"{DIAS_SEMANA_ES[fecha.weekday()]} {fecha.day:02d} "
        f"de {MESES_ES[fecha.month - 1]} de {fecha.year} "
        f"({fecha.strftime('%Y-%m-%d')})"
    )


def construir_contexto_fecha_base_juez_metricas():
    fecha_base = datetime.now()
    manana = fecha_base + timedelta(days=1)
    pasado_manana = fecha_base + timedelta(days=2)
    dias_hasta_proximo_lunes = (7 - fecha_base.weekday()) % 7 or 7
    proximo_lunes = fecha_base + timedelta(days=dias_hasta_proximo_lunes)
    proximo_domingo = proximo_lunes + timedelta(days=6)

    return (
        f"Fecha base actual: {formatear_fecha_juez_metricas(fecha_base)}.\n"
        f'Equivalencia obligatoria: "manana" = {formatear_fecha_juez_metricas(manana)}.\n'
        f'Equivalencia obligatoria: "pasado manana" = {formatear_fecha_juez_metricas(pasado_manana)}.\n'
        f'Equivalencia obligatoria: "la proxima semana" = del '
        f"{formatear_fecha_juez_metricas(proximo_lunes)} "
        f"al {formatear_fecha_juez_metricas(proximo_domingo)}."
    )


def build_error_juez_result_metricas(motivo, raw_json="", latency_s=0.0):
    return {
        "m_coherencia": 0.0,
        "exp_coherencia": "No se pudo evaluar coherencia.",
        "m_fluidez": 0.0,
        "exp_fluidez": "No se pudo evaluar fluidez.",
        "m_cumplimiento": 0.0,
        "exp_cumplimiento": "No se pudo evaluar cumplimiento.",
        "m_integridad": 0.0,
        "exp_integridad": "No se pudo evaluar integridad.",
        "m_claridad": 0.0,
        "exp_claridad": "No se pudo evaluar claridad.",
        "m_correccion": 0.0,
        "exp_correccion": "No se pudo evaluar correccion.",
        "score_total": 0.0,
        "resultado": "FAIL",
        "justificacion": motivo,
        "raw_json": raw_json or "{}",
        "latencia_eval_s": latency_s,
    }


def construir_prompt_metricas(question, caso_de_prueba="", reglas_juez=""):
    contexto_fecha_base = construir_contexto_fecha_base_juez_metricas()

    return f"""
Eres un juez experto en evaluacion conversacional.

Evalua EXCLUSIVAMENTE la calidad metrica de la conversacion respecto al CASO DE PRUEBA.
No evalues funcionalidades operativas en esta salida.

CASO DE PRUEBA:
{caso_de_prueba or 'Sin caso de prueba definido.'}

REGLAS DEL JUEZ:
{reglas_juez or 'Sin reglas para este caso.'}

FECHA BASE PARA EVALUAR FECHAS RELATIVAS:
{contexto_fecha_base}

Metricas obligatorias:
- coherencia
- fluidez
- cumplimiento
- integridad
- claridad
- correccion

Reglas:
- cumplimiento refleja que tanto se cumplio el objetivo del CASO DE PRUEBA.
- score_total debe ser igual a cumplimiento.
- resultado = "FAIL" si cumplimiento esta entre 0.00 y 0.49.
- resultado = "WARNING" si cumplimiento esta entre 0.50 y 0.79.
- resultado = "PASS" si cumplimiento esta entre 0.80 y 1.00.

Devuelve SOLO JSON valido con esta estructura exacta:
{{
  "coherencia": 0.00,
  "exp_coherencia": "texto breve",
  "fluidez": 0.00,
  "exp_fluidez": "texto breve",
  "cumplimiento": 0.00,
  "exp_cumplimiento": "texto breve",
  "integridad": 0.00,
  "exp_integridad": "texto breve",
  "claridad": 0.00,
  "exp_claridad": "texto breve",
  "correccion": 0.00,
  "exp_correccion": "texto breve",
  "score_total": 0.00,
  "resultado": "FAIL",
  "justificacion": "resumen general breve"
}}

CONVERSACION A EVALUAR:
{question}
""".strip()


def llm_judge_metricas(
        question: str,
        caso_de_prueba: str = "",
        reglas_juez: str = "",
        model=MODEL_NAME,
):
    prompt_metricas = construir_prompt_metricas(
        question=question,
        caso_de_prueba=caso_de_prueba,
        reglas_juez=reglas_juez,
    )

    try:
        t0_clas = datetime.now()
        response_clas = obtener_cliente_azure().chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "system",
                    "content": "Responde unicamente con JSON valido y sin markdown.",
                },
                {"role": "user", "content": prompt_metricas},
            ],
            max_tokens=1600,
            temperature=0,
        )
        latency_clas_s = round((datetime.now() - t0_clas).total_seconds(), 2)
        content_clas = (response_clas.choices[0].message.content or "").strip()

        content_clas_clean = content_clas.replace("```json", "").replace("```", "").strip()
        start_clas = content_clas_clean.find("{")
        end_clas = content_clas_clean.rfind("}")
        if start_clas == -1 or end_clas == -1:
            raise ValueError("La respuesta del juez metrica no contiene un JSON valido.")

        parsed_metricas = json.loads(content_clas_clean[start_clas : end_clas + 1])
        if not isinstance(parsed_metricas, dict):
            parsed_metricas = {}

        m_cumplimiento = _normalizar_score_01(parsed_metricas.get("cumplimiento", 0))
        return {
            "m_coherencia": _normalizar_score_01(parsed_metricas.get("coherencia", 0)),
            "exp_coherencia": safe_str(parsed_metricas.get("exp_coherencia", "")),
            "m_fluidez": _normalizar_score_01(parsed_metricas.get("fluidez", 0)),
            "exp_fluidez": safe_str(parsed_metricas.get("exp_fluidez", "")),
            "m_cumplimiento": m_cumplimiento,
            "exp_cumplimiento": safe_str(parsed_metricas.get("exp_cumplimiento", "")),
            "m_integridad": _normalizar_score_01(parsed_metricas.get("integridad", 0)),
            "exp_integridad": safe_str(parsed_metricas.get("exp_integridad", "")),
            "m_claridad": _normalizar_score_01(parsed_metricas.get("claridad", 0)),
            "exp_claridad": safe_str(parsed_metricas.get("exp_claridad", "")),
            "m_correccion": _normalizar_score_01(parsed_metricas.get("correccion", 0)),
            "exp_correccion": safe_str(parsed_metricas.get("exp_correccion", "")),
            "score_total": m_cumplimiento,
            "resultado": clasificar_cumplimiento_metricas(m_cumplimiento),
            "justificacion": safe_str(parsed_metricas.get("justificacion", "")),
            "raw_json": json.dumps(parsed_metricas, ensure_ascii=False, indent=2),
            "latencia_eval_s": latency_clas_s,
        }

    except Exception as e:
        return build_error_juez_result_metricas(
            motivo=f"Error analizando salida del juez metrica: {type(e).__name__}: {e}",
            raw_json=safe_str(locals().get("content_clas", "")),
            latency_s=locals().get("latency_clas_s", 0.0),
        )

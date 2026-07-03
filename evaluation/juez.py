from config import EVAL_PROFILE, MODEL_NAME, TIPO_AGENTE
from evaluation.juez_funcionalidades import (
    FUNCIONALIDADES_JUEZ,
    FUNCIONALIDADES_VISIBLES_REPORTE,
    build_error_juez_result,
    calcular_resumen_funcionalidades,
    llm_judge_funcionalidades,
    normalizar_score_funcionalidad,
)
from evaluation.juez_metricas import (
    _normalizar_score_01,
    build_error_juez_result_metricas,
    llm_judge_metricas as ejecutar_juez_metricas,
)
from evaluation.juez_respuesta import (
    build_error_juez_respuesta,
    llm_judge_respuesta,
)

__all__ = [
    "FUNCIONALIDADES_JUEZ",
    "FUNCIONALIDADES_VISIBLES_REPORTE",
    "normalizar_score_funcionalidad",
    "calcular_resumen_funcionalidades",
    "_normalizar_score_01",
    "build_error_juez_result_metricas",
    "build_default_juez_result",
    "llm_judge_metricas",
]


def _adjuntar_metricas(eval_juez, metricas_eval):
    eval_juez.update(
        {
            "resultado_metricas": metricas_eval.get("resultado", "FAIL"),
            "justificacion_metricas": metricas_eval.get("justificacion", ""),
            "score_total_metricas": metricas_eval.get("score_total", 0.0),
            "m_coherencia": metricas_eval.get("m_coherencia", 0.0),
            "exp_coherencia": metricas_eval.get("exp_coherencia", ""),
            "m_fluidez": metricas_eval.get("m_fluidez", 0.0),
            "exp_fluidez": metricas_eval.get("exp_fluidez", ""),
            "m_cumplimiento": metricas_eval.get("m_cumplimiento", 0.0),
            "exp_cumplimiento": metricas_eval.get("exp_cumplimiento", ""),
            "m_integridad": metricas_eval.get("m_integridad", 0.0),
            "exp_integridad": metricas_eval.get("exp_integridad", ""),
            "m_claridad": metricas_eval.get("m_claridad", 0.0),
            "exp_claridad": metricas_eval.get("exp_claridad", ""),
            "m_correccion": metricas_eval.get("m_correccion", 0.0),
            "exp_correccion": metricas_eval.get("exp_correccion", ""),
            "raw_json_metricas": metricas_eval.get("raw_json", "{}"),
            "latencia_eval_s_metricas": metricas_eval.get("latencia_eval_s", 0.0),
        }
    )
    return eval_juez


EVAL_PROFILE_PIPELINE = {
    "phoenix_cobranzas": "funcionalidades",
    "generic_agentic": "respuesta",
    "no_agentico_default": "respuesta",
}


def _resolver_pipeline() -> str:
    return EVAL_PROFILE_PIPELINE.get(EVAL_PROFILE, "funcionalidades")


def build_default_juez_result(motivo=""):
    pipeline = _resolver_pipeline()
    if pipeline == "respuesta":
        return build_error_juez_respuesta(
            motivo or "No se ejecuto el juez de respuesta."
        )

    return build_error_juez_result(
        motivo or "No se ejecuto el juez por funcionalidades."
    )


def llm_judge_metricas(
        question: str,
        perfil: str = "",
        caso_de_prueba: str = "",
        reglas_juez: str = "",
        model=MODEL_NAME,
):
    pipeline = _resolver_pipeline()
    if pipeline == "funcionalidades":
        eval_juez = llm_judge_funcionalidades(
            question=question,
            perfil=perfil,
            caso_de_prueba=caso_de_prueba,
            reglas_juez=reglas_juez,
            model=model,
        )
    elif pipeline == "respuesta":
        eval_juez = llm_judge_respuesta(
            question=question,
            caso_de_prueba=caso_de_prueba,
            reglas_juez=reglas_juez,
            model=model,
        )
    else:
        eval_juez = build_error_juez_result(
            "Pipeline de evaluacion no soportado. "
            f"EVAL_PROFILE={EVAL_PROFILE!r}, TIPO_AGENTE={TIPO_AGENTE!r}"
        )

    metricas_eval = ejecutar_juez_metricas(
        question=question,
        caso_de_prueba=caso_de_prueba,
        reglas_juez=reglas_juez,
        model=model,
    )

    return _adjuntar_metricas(eval_juez, metricas_eval)

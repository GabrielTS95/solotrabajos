EVAL_PROFILE_PIPELINE = {
    "phoenix_cobranzas": "funcionalidades",
    "phoenix_cobranzas_agentico": "funcionalidades",
    "agentico_default": "respuesta",
}


def resolver_pipeline(eval_profile: str) -> str:
    return EVAL_PROFILE_PIPELINE.get(eval_profile, "funcionalidades")

EVAL_PROFILE_PIPELINE = {
    "phoenix_cobranzas": "funcionalidades",
    "generic_agentic": "respuesta",
    "no_agentico_default": "respuesta",
}


def resolver_pipeline(eval_profile: str) -> str:
    return EVAL_PROFILE_PIPELINE.get(eval_profile, "funcionalidades")

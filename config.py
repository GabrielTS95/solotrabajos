import os
from pathlib import Path

try:
    from dotenv import load_dotenv
except ImportError:
    def load_dotenv(*args, **kwargs):
        return False

BASE_DIR = Path(__file__).resolve().parent
AMBIENTES_PERMITIDOS = {"desa", "certi", "prod"}
TIPOS_AGENTE_PERMITIDOS = {"agentico"}
EVAL_PROFILES_PERMITIDOS = {
    "phoenix_cobranzas",
    "phoenix_cobranzas_agentico",
    "agentico_default",
}
EVAL_PROFILE_ALIASES = {
    "phoenix_cobranzas_agentico": "phoenix_cobranzas",
}
AGENT_ADAPTERS_PERMITIDOS = {"phoenix", "agentico_rest", "text_summarizer"}


def _obtener_app_env() -> str:
    app_env = os.getenv("APP_ENV", "desa").strip().lower()
    if app_env not in AMBIENTES_PERMITIDOS:
        permitidos = ", ".join(sorted(AMBIENTES_PERMITIDOS))
        raise RuntimeError(
            f"APP_ENV invalido: {app_env!r}. Valores permitidos: {permitidos}"
        )
    return app_env


APP_ENV = _obtener_app_env()
CONFIRM_PROD = os.getenv("CONFIRM_PROD", "").strip()
ENV_FILE = BASE_DIR / f".env.{APP_ENV}"

if not ENV_FILE.exists():
    raise RuntimeError(
        f"No existe archivo de ambiente: {ENV_FILE}. "
        "Crea el archivo de ambiente correspondiente y vuelve a ejecutar."
    )

load_dotenv(dotenv_path=ENV_FILE, override=True)

if APP_ENV == "prod" and CONFIRM_PROD != "1":
    raise RuntimeError(
        "APP_ENV=prod requiere definir CONFIRM_PROD=1 en la consola antes de ejecutar."
    )


def _get_required_env(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise RuntimeError(
            f"Variable obligatoria no configurada: {name}. Revisa {ENV_FILE}."
        )
    return value


def _get_required_int_env(name: str) -> int:
    value = _get_required_env(name)
    try:
        return int(value)
    except ValueError as exc:
        raise RuntimeError(
            f"Variable {name} debe ser un numero entero. Valor actual: {value!r}"
        ) from exc


def _get_required_flag_env(name: str) -> bool:
    value = _get_required_env(name)
    if value not in {"0", "1"}:
        raise RuntimeError(
            f"Variable {name} debe ser 0 o 1. Valor actual: {value!r}"
        )
    return value == "1"


def _get_optional_int_env(name: str, default: int) -> int:
    value = os.getenv(name, "").strip()
    if not value:
        return default
    try:
        return int(value)
    except ValueError as exc:
        raise RuntimeError(
            f"Variable {name} debe ser un numero entero. Valor actual: {value!r}"
        ) from exc


def _get_optional_flag_env(name: str, default: bool = False) -> bool:
    value = os.getenv(name, "").strip()
    if not value:
        return default
    if value not in {"0", "1"}:
        raise RuntimeError(
            f"Variable {name} debe ser 0 o 1. Valor actual: {value!r}"
        )
    return value == "1"


def _get_optional_env(name: str, default: str = "") -> str:
    value = os.getenv(name)
    if value is None:
        return default
    value = value.strip()
    return value if value else default


def _get_tipo_agente() -> str:
    tipo_agente = _get_required_env("TIPO_AGENTE").lower()
    if tipo_agente not in TIPOS_AGENTE_PERMITIDOS:
        permitidos = ", ".join(sorted(TIPOS_AGENTE_PERMITIDOS))
        raise RuntimeError(
            f"TIPO_AGENTE invalido: {tipo_agente!r}. Valores permitidos: {permitidos}"
        )
    return tipo_agente


def _get_eval_profile(agent_adapter: str) -> str:
    eval_profile = os.getenv("EVAL_PROFILE", "").strip().lower()
    if not eval_profile:
        if agent_adapter == "phoenix":
            return "phoenix_cobranzas"
        return "agentico_default"

    eval_profile = EVAL_PROFILE_ALIASES.get(eval_profile, eval_profile)
    if eval_profile not in EVAL_PROFILES_PERMITIDOS:
        permitidos = ", ".join(sorted(EVAL_PROFILES_PERMITIDOS))
        raise RuntimeError(
            f"EVAL_PROFILE invalido: {eval_profile!r}. Valores permitidos: {permitidos}"
        )
    return eval_profile


def _get_agent_adapter() -> str:
    agent_adapter = os.getenv("AGENT_ADAPTER", "phoenix").strip().lower()
    if agent_adapter not in AGENT_ADAPTERS_PERMITIDOS:
        permitidos = ", ".join(sorted(AGENT_ADAPTERS_PERMITIDOS))
        raise RuntimeError(
            f"AGENT_ADAPTER invalido: {agent_adapter!r}. "
            f"Valores permitidos: {permitidos}"
        )
    return agent_adapter


TIPO_AGENTE = _get_tipo_agente()
AGENT_ADAPTER = _get_agent_adapter()
EVAL_PROFILE = _get_eval_profile(AGENT_ADAPTER)

AZURE_OPENAI_API_KEY = _get_required_env("AZURE_OPENAI_API_KEY")
AZURE_OPENAI_ENDPOINT = _get_required_env("AZURE_OPENAI_ENDPOINT")
AZURE_OPENAI_API_VERSION = _get_required_env("AZURE_OPENAI_API_VERSION")

# En Azure OpenAI, model=deployment name
MODEL_NAME = _get_required_env("MODEL_NAME")
API_KEY = (
    _get_required_env("BOT_API_KEY")
    if AGENT_ADAPTER == "phoenix"
    else _get_optional_env("BOT_API_KEY")
)

MAX_TURNS_SAFE = _get_required_int_env("MAX_TURNS_SAFE")
MAX_WORKERS = _get_required_int_env("MAX_WORKERS")
DEBUG_HTTP = _get_required_flag_env("DEBUG_HTTP")

URL_CHAT = (
    _get_required_env("URL_CHAT")
    if AGENT_ADAPTER == "phoenix"
    else _get_optional_env("URL_CHAT")
)
CUSTOMER_PROC_URL = (
    _get_required_env("CUSTOMER_PROC_URL")
    if AGENT_ADAPTER == "phoenix"
    else _get_optional_env("CUSTOMER_PROC_URL")
)

AGENTICO_REST_URL = _get_optional_env("AGENTICO_REST_URL")
AGENTICO_REST_API_KEY = _get_optional_env("AGENTICO_REST_API_KEY")
AGENTICO_REST_AUTH_HEADER = _get_optional_env("AGENTICO_REST_AUTH_HEADER", "X-API-key")
AGENTICO_REST_TIMEOUT = _get_optional_int_env("AGENTICO_REST_TIMEOUT", 600)
AGENTICO_REST_VERIFY_SSL = _get_optional_flag_env("AGENTICO_REST_VERIFY_SSL", True)
AGENTICO_REST_RESPONSE_FIELD = _get_optional_env("AGENTICO_REST_RESPONSE_FIELD")
AGENTICO_REST_PAYLOAD_MODE = _get_optional_env(
    "AGENTICO_REST_PAYLOAD_MODE", "default"
).lower()

TEXT_SUMMARIZER_BASE_URL = _get_optional_env("TEXT_SUMMARIZER_BASE_URL")
TEXT_SUMMARIZER_API_KEY = _get_optional_env("TEXT_SUMMARIZER_API_KEY")
TEXT_SUMMARIZER_AUTH_HEADER = _get_optional_env(
    "TEXT_SUMMARIZER_AUTH_HEADER", "Authorization"
)
TEXT_SUMMARIZER_TIMEOUT = _get_optional_int_env("TEXT_SUMMARIZER_TIMEOUT", 600)
TEXT_SUMMARIZER_VERIFY_SSL = _get_optional_flag_env(
    "TEXT_SUMMARIZER_VERIFY_SSL", True
)
TEXT_SUMMARIZER_RESPONSE_FIELD = _get_optional_env(
    "TEXT_SUMMARIZER_RESPONSE_FIELD", "content"
)
TEXT_SUMMARIZER_FORCE_TEXT_EXTRACTION = _get_optional_flag_env(
    "TEXT_SUMMARIZER_FORCE_TEXT_EXTRACTION", True
)

CSV_PATH = _get_required_env("CSV_PATH")
CSV_SEP = _get_required_env("CSV_SEP")
OUTPUT_DIR = _get_required_env("OUTPUT_DIR")
REPORT_TITLE = _get_optional_env("REPORT_TITLE", "Reporte de Evaluacion IA-AGENT")


def obtener_max_workers(total_escenarios: int) -> int:
    return max(1, min(MAX_WORKERS, total_escenarios))

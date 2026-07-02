import os
from pathlib import Path

try:
    from dotenv import load_dotenv
except ImportError:
    def load_dotenv(*args, **kwargs):
        return False


BASE_DIR = Path(__file__).resolve().parent
AMBIENTES_PERMITIDOS = {"desa", "certi", "prod"}
TIPOS_AGENTE_PERMITIDOS = {"agentico", "no_agentico"}


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


def _get_tipo_agente() -> str:
    tipo_agente = _get_required_env("TIPO_AGENTE").lower()
    if tipo_agente not in TIPOS_AGENTE_PERMITIDOS:
        permitidos = ", ".join(sorted(TIPOS_AGENTE_PERMITIDOS))
        raise RuntimeError(
            f"TIPO_AGENTE invalido: {tipo_agente!r}. Valores permitidos: {permitidos}"
        )
    return tipo_agente


AZURE_OPENAI_API_KEY = _get_required_env("AZURE_OPENAI_API_KEY")
AZURE_OPENAI_ENDPOINT = _get_required_env("AZURE_OPENAI_ENDPOINT")
AZURE_OPENAI_API_VERSION = _get_required_env("AZURE_OPENAI_API_VERSION")

# En Azure OpenAI, model=deployment name
MODEL_NAME = _get_required_env("MODEL_NAME")
API_KEY = _get_required_env("BOT_API_KEY")

MAX_TURNS_SAFE = _get_required_int_env("MAX_TURNS_SAFE")
MAX_WORKERS = _get_required_int_env("MAX_WORKERS")
DEBUG_HTTP = _get_required_flag_env("DEBUG_HTTP")
TIPO_AGENTE = _get_tipo_agente()

URL_CHAT = _get_required_env("URL_CHAT")
CUSTOMER_PROC_URL = _get_required_env("CUSTOMER_PROC_URL")

CSV_PATH = _get_required_env("CSV_PATH")
CSV_SEP = _get_required_env("CSV_SEP")
OUTPUT_DIR = _get_required_env("OUTPUT_DIR")


def obtener_max_workers(total_escenarios: int) -> int:
    return max(1, min(MAX_WORKERS, total_escenarios))

import re
from typing import Any


_TRUNCATION_MARKER = "\n[CONTENIDO TRUNCADO POR EL FRAMEWORK]"


def bounded_text(value: str, maximum_chars: int) -> str:
    """Limita el texto enviado al LLM para controlar costo y superficie de ataque."""
    if len(value) <= maximum_chars:
        return value
    available = max(0, maximum_chars - len(_TRUNCATION_MARKER))
    return value[:available] + _TRUNCATION_MARKER


def sanitize_error_message(value: str) -> str:
    """
    Evita imprimir accidentalmente tokens con apariencia de API key.
    No reemplaza el uso correcto de SecretStr ni un gestor de secretos.
    """
    prefixed_secret_patterns = [
        r"(?i)(api[_-]?key\s*[=:]\s*)[^\s,;]+",
        r"(?i)(authorization\s*[=:]\s*bearer\s+)[^\s,;]+",
    ]
    sanitized = value
    for pattern in prefixed_secret_patterns:
        sanitized = re.sub(pattern, r"\1[REDACTED]", sanitized)
    sanitized = re.sub(r"\bapp-[A-Za-z0-9_-]{8,}\b", "app-[REDACTED]", sanitized)
    return sanitized


def without_none(data: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in data.items() if value is not None}


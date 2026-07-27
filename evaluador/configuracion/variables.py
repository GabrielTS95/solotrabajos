from functools import lru_cache
from urllib.parse import urlparse

from pydantic import Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


_LOCAL_HOSTS = {"localhost", "127.0.0.1", "::1"}


def _validate_endpoint(value: str) -> str:
    normalized = value.strip().rstrip("/")
    parsed = urlparse(normalized)

    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise ValueError("El endpoint debe ser una URL HTTP(S) valida.")

    if parsed.scheme == "http" and parsed.hostname not in _LOCAL_HOSTS:
        raise ValueError(
            "Solo se permite HTTP para localhost. Use HTTPS en ambientes remotos."
        )

    return normalized


class Settings(BaseSettings):
    # Agente bajo prueba. Dify es un adaptador, no el centro del evaluador.
    agent_provider: str = Field(default="dify", min_length=1)
    agent_base_url: str | None = None
    agent_endpoint: str | None = None
    agent_api_key: SecretStr | None = None

    # Opciones para conectar agentes por HTTP generico.
    agent_method: str = "POST"
    agent_query_field: str = "query"
    agent_user_field: str = "user"
    agent_answer_path: str = "answer"
    agent_auth_header: str = "Authorization"
    agent_auth_scheme: str = "Bearer"

    # Variables compatibles con Dify.
    dify_base_url: str | None = None
    dify_api_key: SecretStr | None = None

    # Modelo juez.
    foundry_endpoint: str
    foundry_api_key: SecretStr
    foundry_model: str = Field(min_length=1)
    foundry_json_mode: bool = True

    request_timeout_seconds: float = Field(default=45, gt=0, le=180)
    max_user_input_chars: int = Field(default=12_000, ge=1_000, le=100_000)
    max_agent_output_chars: int = Field(default=20_000, ge=1_000, le=100_000)

    report_directory: str = "reports"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @field_validator(
        "agent_base_url",
        "agent_endpoint",
        "dify_base_url",
        "foundry_endpoint",
    )
    @classmethod
    def validate_endpoint(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return _validate_endpoint(value)

    @field_validator("foundry_endpoint")
    @classmethod
    def validate_foundry_v1_path(cls, value: str) -> str:
        if not value.endswith("/openai/v1"):
            raise ValueError("FOUNDRY_ENDPOINT debe terminar en /openai/v1/.")
        return value

    @field_validator("foundry_model")
    @classmethod
    def normalize_model_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("FOUNDRY_MODEL no puede estar vacio.")
        return value

    @field_validator("agent_provider", "agent_method")
    @classmethod
    def normalize_upper_lower_values(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("El valor no puede estar vacio.")
        return value

    @model_validator(mode="after")
    def normalize_agent_settings(self) -> "Settings":
        if self.agent_provider.lower().strip() == "dify":
            if self.agent_base_url is None:
                self.agent_base_url = self.dify_base_url
            if self.agent_api_key is None:
                self.agent_api_key = self.dify_api_key

        if self.agent_provider.lower().strip() not in {"dify", "http"}:
            raise ValueError("AGENT_PROVIDER debe ser dify o http.")

        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()



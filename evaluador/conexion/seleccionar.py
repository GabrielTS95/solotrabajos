from evaluador.conexion.contrato import AgentClient, AgentClientError
from evaluador.conexion.adaptadores.dify import DifyAgentClient
from evaluador.conexion.adaptadores.http_generico import HttpAgentClient
from evaluador.configuracion import Settings


def build_agent_client(settings: Settings) -> AgentClient:
    provider = settings.agent_provider.lower().strip()

    if provider == "dify":
        if settings.agent_base_url is None or settings.agent_api_key is None:
            raise AgentClientError(
                "Para AGENT_PROVIDER=dify configure AGENT_BASE_URL/AGENT_API_KEY "
                "o DIFY_BASE_URL/DIFY_API_KEY."
            )
        return DifyAgentClient(
            base_url=settings.agent_base_url,
            api_key=settings.agent_api_key.get_secret_value(),
            timeout_seconds=settings.request_timeout_seconds,
        )

    if provider == "http":
        if settings.agent_endpoint is None:
            raise AgentClientError("Para AGENT_PROVIDER=http configure AGENT_ENDPOINT.")
        api_key = (
            settings.agent_api_key.get_secret_value()
            if settings.agent_api_key is not None
            else None
        )
        return HttpAgentClient(
            endpoint=settings.agent_endpoint,
            timeout_seconds=settings.request_timeout_seconds,
            answer_path=settings.agent_answer_path,
            query_field=settings.agent_query_field,
            user_field=settings.agent_user_field,
            method=settings.agent_method,
            api_key=api_key,
            auth_header=settings.agent_auth_header,
            auth_scheme=settings.agent_auth_scheme,
        )

    raise AgentClientError(
        f"AGENT_PROVIDER no soportado: {settings.agent_provider}. Use dify o http."
    )



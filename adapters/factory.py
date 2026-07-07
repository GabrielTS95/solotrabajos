from adapters.agentico_rest.agent import AgenticoRestClient
from adapters.phoenix.agent import PhoenixAgentClient
from config import AGENT_ADAPTER


AGENT_CLIENTS = {
    "agentico_rest": AgenticoRestClient,
    "phoenix": PhoenixAgentClient,
}


def build_agent_client(adapter_name=None):
    resolved_adapter = (adapter_name or AGENT_ADAPTER).strip().lower()
    client_cls = AGENT_CLIENTS.get(resolved_adapter)
    if client_cls is None:
        available = ", ".join(sorted(AGENT_CLIENTS))
        raise RuntimeError(
            f"AGENT_ADAPTER no soportado: {resolved_adapter!r}. "
            f"Valores disponibles: {available}"
        )
    return client_cls()

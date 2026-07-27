import time
from typing import Any

import httpx

from evaluador.conexion.contrato import AgentClientError
from evaluador.evaluacion.modelos import AgentResponse
from evaluador.utilidades.seguridad import sanitize_error_message


class HttpAgentClient:
    """
    Adaptador para agentes expuestos mediante un endpoint HTTP JSON.

    El cuerpo de la solicitud usa nombres de campos configurables:
    {"query": "...", "user": "..."} por defecto.

    La respuesta se lee desde una ruta dentro del JSON:
    "answer", "data.answer" o "choices.0.message.content".
    """

    def __init__(
        self,
        endpoint: str,
        timeout_seconds: float,
        answer_path: str = "answer",
        query_field: str = "query",
        user_field: str = "user",
        method: str = "POST",
        api_key: str | None = None,
        auth_header: str = "Authorization",
        auth_scheme: str = "Bearer",
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self._endpoint = endpoint
        self._timeout = httpx.Timeout(timeout_seconds)
        self._answer_path = answer_path
        self._query_field = query_field
        self._user_field = user_field
        self._method = method.upper()
        self._api_key = api_key
        self._auth_header = auth_header
        self._auth_scheme = auth_scheme
        self._transport = transport

    def send_message(self, query: str, user_id: str) -> AgentResponse:
        payload = {
            self._query_field: query,
            self._user_field: user_id,
        }
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        if self._api_key:
            auth_value = self._api_key
            if self._auth_scheme:
                auth_value = f"{self._auth_scheme} {auth_value}"
            headers[self._auth_header] = auth_value

        started_at = time.perf_counter()

        try:
            with httpx.Client(
                timeout=self._timeout,
                follow_redirects=False,
                verify=True,
                transport=self._transport,
            ) as client:
                response = client.request(
                    self._method,
                    self._endpoint,
                    headers=headers,
                    json=payload,
                )
        except httpx.TimeoutException as exc:
            raise AgentClientError("El agente excedio el tiempo maximo de espera.") from exc
        except httpx.HTTPError as exc:
            message = sanitize_error_message(str(exc))
            raise AgentClientError(f"No fue posible conectar con el agente: {message}") from exc

        latency_ms = round((time.perf_counter() - started_at) * 1_000)

        if response.status_code < 200 or response.status_code >= 300:
            raise AgentClientError(f"El agente respondio con HTTP {response.status_code}.")

        try:
            data = response.json()
        except ValueError as exc:
            raise AgentClientError("El agente no devolvio un JSON valido.") from exc

        answer = extract_json_path(data, self._answer_path)
        if not isinstance(answer, str):
            raise AgentClientError(
                f"La respuesta del agente no contiene texto en '{self._answer_path}'."
            )

        return AgentResponse(
            answer=answer,
            status_code=response.status_code,
            latency_ms=latency_ms,
        )


def extract_json_path(data: Any, path: str) -> Any:
    current = data
    for part in path.split("."):
        if isinstance(current, dict):
            current = current.get(part)
        elif isinstance(current, list) and part.isdigit():
            index = int(part)
            current = current[index] if 0 <= index < len(current) else None
        else:
            return None
    return current



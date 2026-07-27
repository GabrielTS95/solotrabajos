import time

import httpx

from evaluador.conexion.contrato import AgentClientError
from evaluador.evaluacion.modelos import AgentResponse
from evaluador.utilidades.seguridad import sanitize_error_message


class DifyAgentClient:
    def __init__(
        self,
        base_url: str,
        api_key: str,
        timeout_seconds: float,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._timeout = httpx.Timeout(timeout_seconds)

    def send_message(self, query: str, user_id: str) -> AgentResponse:
        payload = {
            "inputs": {},
            "query": query,
            "response_mode": "blocking",
            "user": user_id,
        }
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

        started_at = time.perf_counter()

        try:
            with httpx.Client(
                timeout=self._timeout,
                follow_redirects=False,
                verify=True,
            ) as client:
                response = client.post(
                    f"{self._base_url}/chat-messages",
                    headers=headers,
                    json=payload,
                )
        except httpx.TimeoutException as exc:
            raise AgentClientError("El agente Dify excedio el tiempo maximo de espera.") from exc
        except httpx.HTTPError as exc:
            message = sanitize_error_message(str(exc))
            raise AgentClientError(f"No fue posible conectar con Dify: {message}") from exc

        latency_ms = round((time.perf_counter() - started_at) * 1_000)

        if response.status_code != 200:
            raise AgentClientError(f"Dify respondio con HTTP {response.status_code}.")

        try:
            data = response.json()
        except ValueError as exc:
            raise AgentClientError("Dify no devolvio un JSON valido.") from exc

        answer = data.get("answer")
        if not isinstance(answer, str):
            raise AgentClientError("La respuesta de Dify no contiene el campo 'answer'.")

        return AgentResponse(
            answer=answer,
            status_code=response.status_code,
            latency_ms=latency_ms,
            conversation_id=data.get("conversation_id"),
            message_id=data.get("message_id"),
        )



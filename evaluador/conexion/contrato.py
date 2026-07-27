from typing import Protocol

from evaluador.evaluacion.modelos import AgentResponse


class AgentClientError(RuntimeError):
    pass


class AgentClient(Protocol):
    def send_message(self, query: str, user_id: str) -> AgentResponse:
        """Envia una pregunta al agente bajo prueba y devuelve su respuesta."""



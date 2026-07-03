from dataclasses import dataclass, field
from typing import Any, Dict, Protocol

#Resultado de preparar un escenario
@dataclass
class PreparedScenario:
    payload: Dict[str, Any] = field(default_factory=dict)
    prompt_data: Dict[str, str] = field(default_factory=dict)
    evaluator_profile: str = ""

#Representa una sesión/chat iniciada
@dataclass
class ChatSession:
    chat_id: str
    raw: Dict[str, Any] = field(default_factory=dict)

#Respuesta estandar de cualquier agente
@dataclass
class AgentResponse:
    text: str
    latency_s: float = 0.0
    exit_status: int = 0
    raw: Any = None


class AgentClient(Protocol):
    name: str

    def prepare_scenario(self, scenario_data: Dict[str, Any]) -> PreparedScenario:
        ...

    def start_chat(self, prepared: PreparedScenario) -> ChatSession:
        ...

    def send_message(self, session: ChatSession, message: str) -> AgentResponse:
        ...

class UserSimulationClient(Protocol):
    def simulate_user(
            self,
            scenario: Any,
            prepared: PreparedScenario,
            history: list,
    ) -> str:
        ...

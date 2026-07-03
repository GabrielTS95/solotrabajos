from uuid import uuid4

from adapters.no_agentico_rest.client import send_rest_message
from core.contracts import ChatSession, PreparedScenario
from core.utils import safe_str


class NoAgenticoRestClient:
    name = "no_agentico_rest"

    def prepare_scenario(self, scenario_data):
        id_test = safe_str(scenario_data.get("id_test"))
        return PreparedScenario(
            payload={
                "adapter": self.name,
                "id_test": id_test,
                "metadata": scenario_data,
            },
            prompt_data={},
            evaluator_profile=safe_str(
                scenario_data.get("perfil_juez")
                or scenario_data.get("tipo_cliente")
                or "general"
            ),
        )

    def start_chat(self, prepared):
        id_test = safe_str(prepared.payload.get("id_test"))
        chat_id = id_test or f"no-agentico-{uuid4().hex[:12]}"
        return ChatSession(
            chat_id=chat_id,
            raw={
                "prepared_payload": prepared.payload,
                "history": [],
            },
        )

    def send_message(self, session, message):
        return send_rest_message(session, message)

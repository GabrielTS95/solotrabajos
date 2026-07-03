from adapters.phoenix.client import (
    add_new_cic_to_customer_proc,
    create_chat_and_headers,
    send_bot_message,
)
from adapters.phoenix.payload import (
    generar_payload,
    obtener_datos_prompt_desde_payload,
)
from core.contracts import AgentResponse, ChatSession, PreparedScenario
from adapters.phoenix.prompts import get_prompt_por_tipo
from adapters.phoenix.simulator import llamada_user_simulator
from core.utils import safe_str


class PhoenixAgentClient:
    name = "phoenix"

    def prepare_scenario(self, scenario_data):
        payload = generar_payload(scenario_data)
        prompt_data = obtener_datos_prompt_desde_payload(payload)
        evaluator_profile = safe_str(
            payload.get("customer_data", {}).get("classification", "")
        )
        return PreparedScenario(
            payload=payload,
            prompt_data=prompt_data,
            evaluator_profile=evaluator_profile,
        )

    def start_chat(self, prepared):
        add_new_cic_to_customer_proc(prepared.payload)
        chat_id, url_msg, headers_msg = create_chat_and_headers(prepared.payload)
        return ChatSession(
            chat_id=chat_id,
            raw={
                "url_msg": url_msg,
                "headers_msg": headers_msg,
            },
        )

    def send_message(self, session, message):
        bot_text, bot_lat, exit_status, data = send_bot_message(
            session.raw["url_msg"],
            session.raw["headers_msg"],
            message,
        )
        return AgentResponse(
            text=bot_text,
            latency_s=bot_lat,
            exit_status=exit_status,
            raw=data,
        )

    def _build_simulator_prompt(self, scenario, prepared):
        prompt_data = prepared.prompt_data
        profile = scenario.simulator_profile
        return get_prompt_por_tipo(
            scenario.client_type,
            prompt_data.get("nombre_completo", ""),
            prompt_data.get("deuda_soles", ""),
            prompt_data.get("deuda_dolares", ""),
            profile.get("identidad_del_cliente", ""),
            profile.get("voluntad_de_pago", ""),
            profile.get("capacidad_pago", ""),
            profile.get("estilo_respuesta", ""),
            profile.get("actitud_comportamiento", ""),
            profile.get("barreras_whatssapp", ""),
            profile.get("frases_comunes", ""),
            profile.get("reglas_muy_importante", ""),
        )

    def simulate_user(self, scenario, prepared, history):
        prompt_cliente = self._build_simulator_prompt(scenario, prepared)
        return llamada_user_simulator(prompt_cliente, history)

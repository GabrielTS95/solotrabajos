import unittest
from unittest.mock import patch

from adapters.agentico_rest.agent import AgenticoRestClient
from adapters.factory import build_agent_client
from core.contracts import AgentResponse, ChatSession, PreparedScenario
from core.runner import ejecutar_escenario
from core.scenario import scenario_from_row


class MockAgentClient:
    name = "mock"

    def prepare_scenario(self, scenario_data):
        return PreparedScenario(
            payload={"adapter": "mock"},
            prompt_data={
                "nombre_completo": "Cliente Demo",
                "cic": "123",
                "dni": "456",
                "cel": "789",
                "deuda_soles": "100.0",
                "deuda_dolares": "0.0",
                "tipo_deuda": "Demo",
            },
            evaluator_profile="mock-profile",
        )

    def start_chat(self, prepared):
        return ChatSession(chat_id="mock-chat", raw={})

    def send_message(self, session, message):
        return AgentResponse(
            text=f"Respuesta mock a: {message}",
            latency_s=0.01,
            exit_status=1,
            raw={"ok": True},
        )


def fake_judge(*args, **kwargs):
    return {
        "resultado": "PASS",
        "justificacion": "Evaluacion mock.",
        "score_total": 1.0,
        "total_cumple": 0,
        "total_no_cumple": 0,
        "total_no_aplica": 0,
        "total_aplicables": 1,
        "raw_json": "{}",
        "latencia_eval_s": 0.0,
        "resultado_metricas": "PASS",
        "justificacion_metricas": "Metricas mock.",
        "score_total_metricas": 1.0,
    }


class FakeRestResponse:
    text = ""

    def raise_for_status(self):
        return None

    def json(self):
        return {
            "respuesta": "Respuesta REST de prueba",
            "exit_status": 1,
        }


class AdapterRunnerTests(unittest.TestCase):
    def test_factory_resuelve_phoenix(self):
        self.assertEqual(build_agent_client("phoenix").name, "phoenix")
        self.assertTrue(hasattr(build_agent_client("phoenix"), "simulate_user"))

    def test_factory_resuelve_agentico_rest(self):
        client = build_agent_client("agentico_rest")
        self.assertEqual(client.name, "agentico_rest")
        self.assertFalse(hasattr(client, "simulate_user"))

    def test_factory_rechaza_adapter_desconocido(self):
        with self.assertRaises(RuntimeError):
            build_agent_client("desconocido")

    def test_scenario_from_row_normaliza_campos_base(self):
        scenario = scenario_from_row(
            0,
            {
                "id_test": "CPX",
                "mensaje_inicio": "hola",
                "secuencia_mensaje": "uno\ndos",
                "caso_de_prueba": "caso",
                "tipo_cliente": "I",
                "reglas_negocio_juez": "regla juez",
            },
        )

        self.assertEqual(scenario.id_test, "CPX")
        self.assertEqual(scenario.initial_message, "hola")
        self.assertEqual(scenario.sequence_messages, ["uno", "dos"])
        self.assertEqual(scenario.judge_rules, "regla juez")

    def test_runner_usa_agent_client_mock_sin_llamadas_externas(self):
        user = {
            "id_test": "CP-MOCK",
            "mensaje_inicio": "hola",
            "secuencia_mensaje": "",
            "caso_de_prueba": "Validar flujo mock",
            "tipo_cliente": "I",
            "reglas_negocio_juez": "Debe responder.",
            "reglas_negocio_cliente": "Regla cliente.",
        }

        with patch("core.runner.llm_judge_metricas", side_effect=fake_judge):
            row = ejecutar_escenario(
                0,
                user,
                agent_client=MockAgentClient(),
            )

        self.assertEqual(row["chat_id"], "mock-chat")
        self.assertEqual(row["status_prueba"], "PASS")
        self.assertEqual(row["score_total_metricas"], 1.0)
        self.assertIn("Respuesta mock", row["answer_last_bot"])
        self.assertIn('"adapter": "mock"', row["payload"])

    def test_runner_permite_adapter_agentico_sin_user_simulator(self):
        user = {
            "id_test": "CP-MOCK",
            "mensaje_inicio": "hola",
            "secuencia_mensaje": "",
            "caso_de_prueba": "Validar flujo mock",
            "tipo_cliente": "I",
            "reglas_negocio_juez": "Debe responder.",
            "reglas_negocio_cliente": "Regla cliente.",
        }

        with patch("core.runner.llm_judge_metricas", side_effect=fake_judge):
            row = ejecutar_escenario(
                0,
                user,
                agent_client=MockAgentClient(),
            )

        self.assertEqual(row["status"], "OK")
        self.assertEqual(row["status_prueba"], "PASS")

    def test_agentico_rest_envia_mensaje_y_parsea_respuesta(self):
        client = AgenticoRestClient()
        prepared = client.prepare_scenario(
            {
                "id_test": "CP-REST",
                "mensaje_inicio": "hola",
                "caso_de_prueba": "Caso REST",
            }
        )
        session = client.start_chat(prepared)

        with patch(
            "adapters.agentico_rest.client.AGENTICO_REST_URL",
            "https://example.test/agent",
        ):
            with patch(
                "adapters.agentico_rest.client.requests.post",
                return_value=FakeRestResponse(),
            ) as post:
                response = client.send_message(session, "hola")

        self.assertEqual(response.text, "Respuesta REST de prueba")
        self.assertEqual(response.exit_status, 1)
        self.assertEqual(session.chat_id, "CP-REST")
        self.assertEqual(post.call_args.kwargs["json"]["message"], "hola")
        self.assertEqual(post.call_args.kwargs["json"]["id_test"], "CP-REST")


if __name__ == "__main__":
    unittest.main()

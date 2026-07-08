import unittest
from unittest.mock import patch

from adapters.text_summarizer.agent import TextSummarizerAgentClient


class FakeResponse:
    text = ""

    def __init__(self, data):
        self._data = data

    def raise_for_status(self):
        return None

    def json(self):
        return self._data


class TextSummarizerAdapterTests(unittest.TestCase):
    def test_crea_conversacion_y_envia_mensaje_con_conversation_id(self):
        client = TextSummarizerAgentClient()
        prepared = client.prepare_scenario(
            {
                "id_test": "TS001",
                "mensaje_inicio": "Si deseo ir de vacaciones.",
                "document_path": "",
                "caso_de_prueba": "Validar respuesta de viaje",
            }
        )

        conversation_response = FakeResponse(
            {
                "conversation_id": "conv_123",
                "created_at": "2026-07-08T15:42:38.908944",
            }
        )
        message_response = FakeResponse(
            {
                "type": "text",
                "content": "Respuesta extraida desde content.",
                "metadata": {
                    "conversation_id": "conv_123",
                    "usage_tokens": 100,
                    "model_name": "gpt-4o-mini",
                },
            }
        )

        with patch(
            "adapters.text_summarizer.client.TEXT_SUMMARIZER_BASE_URL",
            "https://example.test",
        ):
            with patch(
                "adapters.text_summarizer.client.requests.post",
                side_effect=[conversation_response, message_response],
            ) as post:
                session = client.start_chat(prepared)
                response = client.send_message(session, "Si deseo ir de vacaciones.")

        self.assertEqual(session.chat_id, "conv_123")
        self.assertEqual(response.text, "Respuesta extraida desde content.")
        self.assertEqual(session.raw["history"][0]["content"], "Si deseo ir de vacaciones.")
        self.assertEqual(session.raw["history"][1]["content"], response.text)

        create_call = post.call_args_list[0]
        message_call = post.call_args_list[1]
        self.assertEqual(
            create_call.args[0],
            "https://example.test/api/v1/conversations/",
        )
        self.assertEqual(
            message_call.args[0],
            "https://example.test/api/v1/conversations/conv_123/",
        )
        self.assertEqual(
            message_call.kwargs["json"]["message"],
            "Si deseo ir de vacaciones.",
        )
        self.assertEqual(message_call.kwargs["json"]["trace"]["id_test"], "TS001")
        self.assertFalse(message_call.kwargs["json"]["trace"]["document_uploaded"])


if __name__ == "__main__":
    unittest.main()

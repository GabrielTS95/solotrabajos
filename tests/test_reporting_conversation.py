import json
import unittest

from reporting.report import formatear_conversacion_reporte


class ReportingConversationTests(unittest.TestCase):
    def test_formatea_conversacion_text_summarizer(self):
        row = {
            "payload": json.dumps({"adapter": "text_summarizer"}),
            "conversa": json.dumps(
                [
                    ["usuario", "Si deseo ir de vacaciones."],
                    ["bot", "Respuesta desde content."],
                ],
                ensure_ascii=False,
            ),
            "mensaje_inicio": "fallback usuario",
            "answer_last_bot": "fallback bot",
        }

        conversa = formatear_conversacion_reporte(row)

        self.assertIn("[CLIENTE] Si deseo ir de vacaciones.", conversa)
        self.assertIn("[TEXT SUMMARIZER] Respuesta desde content.", conversa)

    def test_conversacion_usa_fallback_si_conversa_viene_vacia(self):
        row = {
            "payload": json.dumps({"adapter": "text_summarizer"}),
            "conversa": "",
            "mensaje_inicio": "Hola",
            "answer_last_bot": "Respuesta final",
        }

        conversa = formatear_conversacion_reporte(row)

        self.assertIn("[CLIENTE] Hola", conversa)
        self.assertIn("[TEXT SUMMARIZER] Respuesta final", conversa)


if __name__ == "__main__":
    unittest.main()

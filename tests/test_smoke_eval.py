import unittest

from evaluation.juez_funcionalidades import get_prompt_juez
from evaluation.juez_metricas import construir_prompt_metricas


class SmokeEvalTests(unittest.TestCase):
    def test_prompt_funcionalidades_se_construye(self):
        prompt = get_prompt_juez(
            question="Conversacion de prueba",
            perfil="Perfil demo",
            caso_de_prueba="Caso demo",
            reglas_juez="Regla demo",
        )
        self.assertIn("FECHA BASE PARA EVALUAR FECHAS RELATIVAS", prompt)
        self.assertIn("FUNCIONALIDADES A EVALUAR", prompt)

    def test_prompt_metricas_se_construye(self):
        prompt = construir_prompt_metricas(
            question="Conversacion de prueba",
            caso_de_prueba="Caso demo",
            reglas_juez="Regla demo",
        )
        self.assertIn("FECHA BASE PARA EVALUAR FECHAS RELATIVAS", prompt)
        self.assertIn("Metricas obligatorias", prompt)


if __name__ == "__main__":
    unittest.main()


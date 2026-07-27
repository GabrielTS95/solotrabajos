import json

from openai import APIConnectionError, APIStatusError, APITimeoutError
from pydantic import ValidationError

from evaluador.juez.cliente_foundry import FoundryClient
from evaluador.evaluacion.modelos import AgentResponse, JudgeAssessment, TestCase
from evaluador.utilidades.seguridad import bounded_text, sanitize_error_message
from evaluador.juez.instrucciones import PROMPT_SISTEMA, construir_prompt_usuario


class JudgeExecutionError(RuntimeError):
    pass


class FoundryJudge:
    def __init__(
        self,
        client: FoundryClient,
        max_user_input_chars: int,
        max_agent_output_chars: int,
    ) -> None:
        self._foundry = client
        self._max_user_input_chars = max_user_input_chars
        self._max_agent_output_chars = max_agent_output_chars

    def evaluate(
        self,
        test_case: TestCase,
        agent_response: AgentResponse,
    ) -> JudgeAssessment:
        pregunta_usuario_segura = bounded_text(
            test_case.query,
            self._max_user_input_chars,
        )
        respuesta_agente_segura = bounded_text(
            agent_response.answer,
            self._max_agent_output_chars,
        )

        prompt = construir_prompt_usuario(
            test_case=test_case,
            pregunta_usuario=pregunta_usuario_segura,
            respuesta_agente=respuesta_agente_segura,
        )

        request = {
            "model": self._foundry.model,
            "messages": [
                {"role": "system", "content": PROMPT_SISTEMA},
                {"role": "user", "content": prompt},
            ],
        }

        if self._foundry.json_mode:
            request["response_format"] = {"type": "json_object"}

        try:
            response = self._foundry.client.chat.completions.create(**request)
        except APITimeoutError as exc:
            raise JudgeExecutionError(
                "Foundry excedió el tiempo máximo de espera."
            ) from exc
        except APIConnectionError as exc:
            raise JudgeExecutionError(
                "No fue posible conectar con Foundry."
            ) from exc
        except APIStatusError as exc:
            # No se expone el body completo ni headers remotos.
            raise JudgeExecutionError(
                f"Foundry respondió con HTTP {exc.status_code}."
            ) from exc
        except Exception as exc:
            message = sanitize_error_message(str(exc))
            raise JudgeExecutionError(
                f"Error inesperado al ejecutar el juez: {message}"
            ) from exc

        if not response.choices:
            raise JudgeExecutionError("Foundry no devolvió alternativas.")

        content = response.choices[0].message.content
        if not content:
            raise JudgeExecutionError("Foundry devolvió una respuesta vacía.")

        normalized = self._normalize_json(content)

        try:
            raw_assessment = json.loads(normalized)
            assessment = JudgeAssessment.model_validate(raw_assessment)
        except json.JSONDecodeError as exc:
            raise JudgeExecutionError(
                "El juez no devolvió un JSON válido."
            ) from exc
        except ValidationError as exc:
            raise JudgeExecutionError(
                "La salida del juez no cumple el contrato esperado."
            ) from exc

        if assessment.test_case_id != test_case.id:
            raise JudgeExecutionError(
                "El juez devolvió un test_case_id diferente al caso evaluado."
            )

        return assessment

    @staticmethod
    def _normalize_json(content: str) -> str:
        value = content.strip()
        if value.startswith("```json") and value.endswith("```"):
            value = value[7:-3].strip()
        elif value.startswith("```") and value.endswith("```"):
            value = value[3:-3].strip()
        return value


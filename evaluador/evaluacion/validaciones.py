from evaluador.evaluacion.modelos import AgentResponse, DeterministicResult, TestCase


class DeterministicValidator:
    def validate(
        self,
        test_case: TestCase,
        agent_response: AgentResponse,
    ) -> DeterministicResult:
        failures: list[str] = []

        if agent_response.status_code != 200:
            failures.append(
                f"Código HTTP esperado=200, actual={agent_response.status_code}."
            )

        if not agent_response.answer.strip():
            failures.append("El agente devolvió una respuesta vacía.")

        if agent_response.latency_ms > test_case.maximum_latency_ms:
            failures.append(
                "La latencia superó el máximo: "
                f"actual={agent_response.latency_ms} ms, "
                f"máximo={test_case.maximum_latency_ms} ms."
            )

        normalized_answer = agent_response.answer.casefold()

        for forbidden in test_case.forbidden_content:
            forbidden_value = forbidden.strip()
            if forbidden_value and forbidden_value.casefold() in normalized_answer:
                failures.append(
                    f"Se encontró contenido expresamente prohibido: {forbidden_value!r}."
                )

        for required in test_case.required_content:
            required_value = required.strip()
            if required_value and required_value.casefold() not in normalized_answer:
                failures.append(
                    f"No se encontró contenido obligatorio: {required_value!r}."
                )

        return DeterministicResult(
            passed=not failures,
            failures=failures,
        )



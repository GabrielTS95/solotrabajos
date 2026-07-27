from openai import OpenAI


class FoundryClient:
    """
    Encapsula el SDK oficial compatible con el endpoint v1 de Foundry.
    """

    def __init__(
        self,
        endpoint: str,
        api_key: str,
        model: str,
        timeout_seconds: float,
        json_mode: bool,
    ) -> None:
        self.model = model
        self.json_mode = json_mode
        self.client = OpenAI(
            base_url=endpoint.rstrip("/") + "/",
            api_key=api_key,
            timeout=timeout_seconds,
            max_retries=2,
        )



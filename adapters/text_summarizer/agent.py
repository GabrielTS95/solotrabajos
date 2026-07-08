from adapters.text_summarizer.client import (
    create_conversation,
    send_conversation_message,
    upload_document,
)
from core.contracts import ChatSession, PreparedScenario
from core.utils import safe_str


class TextSummarizerAgentClient:
    name = "text_summarizer"

    def prepare_scenario(self, scenario_data):
        document_path = safe_str(scenario_data.get("document_path"))
        id_test = safe_str(scenario_data.get("id_test"))
        return PreparedScenario(
            payload={
                "adapter": self.name,
                "id_test": id_test,
                "document_path": document_path,
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
        conversation_data = create_conversation()
        conversation_id = safe_str(conversation_data.get("conversation_id")).strip()
        created_at = safe_str(conversation_data.get("created_at"))

        document_path = safe_str(prepared.payload.get("document_path"))
        document_data = upload_document(document_path) if document_path else None

        return ChatSession(
            chat_id=conversation_id,
            raw={
                "conversation_id": conversation_id,
                "created_at": created_at,
                "prepared_payload": prepared.payload,
                "document_data": document_data,
                "history": [],
            },
        )

    def send_message(self, session, message):
        prepared_payload = session.raw.get("prepared_payload", {})
        trace = {
            "id_test": safe_str(prepared_payload.get("id_test")),
            "adapter": self.name,
            "document_uploaded": bool(session.raw.get("document_data")),
        }

        session.raw.setdefault("history", []).append(
            {"role": "user", "content": safe_str(message)}
        )

        response = send_conversation_message(
            conversation_id=session.raw["conversation_id"],
            message=message,
            trace=trace,
        )

        session.raw.setdefault("history", []).append(
            {
                "role": "assistant",
                "content": response.text,
                "raw": response.raw,
            }
        )
        return response

import json
from datetime import datetime

import requests

from config import (
    AGENTICO_REST_API_KEY,
    AGENTICO_REST_AUTH_HEADER,
    AGENTICO_REST_PAYLOAD_MODE,
    AGENTICO_REST_RESPONSE_FIELD,
    AGENTICO_REST_TIMEOUT,
    AGENTICO_REST_URL,
    AGENTICO_REST_VERIFY_SSL,
)
from core.contracts import AgentResponse
from core.utils import safe_str


def _headers():
    headers = {"Content-Type": "application/json"}
    if AGENTICO_REST_API_KEY:
        headers[AGENTICO_REST_AUTH_HEADER] = AGENTICO_REST_API_KEY
    return headers


def _get_path(data, path):
    current = data
    for part in path.split("."):
        if isinstance(current, list):
            try:
                current = current[int(part)]
            except (ValueError, IndexError):
                return None
        elif isinstance(current, dict):
            current = current.get(part)
        else:
            return None
    return current


def _extract_text(data):
    configured_field = safe_str(AGENTICO_REST_RESPONSE_FIELD).strip()
    if configured_field:
        configured_value = _get_path(data, configured_field)
        if configured_value is not None:
            return safe_str(configured_value)

    if isinstance(data, str):
        return data

    if not isinstance(data, dict):
        return safe_str(data)

    candidate_paths = [
        "content",
        "answer",
        "respuesta",
        "response",
        "text",
        "message",
        "message.content",
        "output",
        "result",
        "data.content",
        "data.answer",
        "data.respuesta",
        "choices.0.message.content",
    ]
    for path in candidate_paths:
        value = _get_path(data, path)
        if value not in (None, ""):
            return safe_str(value)

    return json.dumps(data, ensure_ascii=False)


def _extract_exit_status(data):
    if not isinstance(data, dict):
        return 0

    candidates = [
        data.get("exit_status"),
        _get_path(data, "metadata.outputs.exit_status"),
        _get_path(data, "data.exit_status"),
    ]
    for value in candidates:
        try:
            if value is not None:
                return int(value)
        except (TypeError, ValueError):
            pass

    if data.get("done") is True or data.get("final") is True:
        return 1
    return 0


def _build_payload(session, message):
    if AGENTICO_REST_PAYLOAD_MODE == "message_only":
        return {"message": message}

    history = session.raw.setdefault("history", [])
    prepared_payload = session.raw.get("prepared_payload", {})
    return {
        "message": message,
        "session_id": session.chat_id,
        "id_test": prepared_payload.get("id_test", ""),
        "history": history,
        "metadata": prepared_payload.get("metadata", {}),
    }


def send_rest_message(session, message):
    if not AGENTICO_REST_URL:
        raise RuntimeError(
            "AGENTICO_REST_URL no configurado para AGENT_ADAPTER=agentico_rest"
        )

    payload = _build_payload(session, message)
    session.raw.setdefault("history", []).append(
        {"role": "user", "content": safe_str(message)}
    )

    t0 = datetime.now()
    response = requests.post(
        AGENTICO_REST_URL,
        json=payload,
        headers=_headers(),
        timeout=AGENTICO_REST_TIMEOUT,
        verify=AGENTICO_REST_VERIFY_SSL,
    )
    latency_s = round((datetime.now() - t0).total_seconds(), 2)
    response.raise_for_status()

    try:
        data = response.json()
    except ValueError:
        data = response.text

    text = _extract_text(data)
    session.raw.setdefault("history", []).append(
        {"role": "assistant", "content": text}
    )
    return AgentResponse(
        text=text,
        latency_s=latency_s,
        exit_status=_extract_exit_status(data),
        raw=data,
    )

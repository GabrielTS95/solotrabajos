import json
from datetime import datetime
from pathlib import Path

import requests

from config import (
    TEXT_SUMMARIZER_API_KEY,
    TEXT_SUMMARIZER_AUTH_HEADER,
    TEXT_SUMMARIZER_BASE_URL,
    TEXT_SUMMARIZER_FORCE_TEXT_EXTRACTION,
    TEXT_SUMMARIZER_RESPONSE_FIELD,
    TEXT_SUMMARIZER_TIMEOUT,
    TEXT_SUMMARIZER_VERIFY_SSL,
)
from core.contracts import AgentResponse
from core.utils import safe_str


def _base_url():
    base_url = safe_str(TEXT_SUMMARIZER_BASE_URL).strip().rstrip("/")
    if not base_url:
        raise RuntimeError(
            "TEXT_SUMMARIZER_BASE_URL no configurado para "
            "AGENT_ADAPTER=text_summarizer"
        )
    return base_url


def _headers(json_content=True):
    headers = {"Accept": "*/*"}
    if json_content:
        headers["Content-Type"] = "application/json"
    if TEXT_SUMMARIZER_API_KEY:
        headers[TEXT_SUMMARIZER_AUTH_HEADER] = TEXT_SUMMARIZER_API_KEY
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
    configured_field = safe_str(TEXT_SUMMARIZER_RESPONSE_FIELD).strip()
    if configured_field:
        configured_value = _get_path(data, configured_field)
        if configured_value not in (None, ""):
            return safe_str(configured_value)

    if isinstance(data, str):
        return data

    if not isinstance(data, dict):
        return safe_str(data)

    candidate_paths = [
        "content",
        "message",
        "response",
        "answer",
        "text",
        "summary",
        "result",
        "data.content",
        "data.message",
        "data.response",
        "data.answer",
        "data.summary",
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


def create_conversation():
    url = f"{_base_url()}/api/v1/conversations/"
    response = requests.post(
        url,
        headers=_headers(json_content=False),
        data="",
        timeout=TEXT_SUMMARIZER_TIMEOUT,
        verify=TEXT_SUMMARIZER_VERIFY_SSL,
    )
    response.raise_for_status()
    data = response.json()

    conversation_id = safe_str(data.get("conversation_id")).strip()
    if not conversation_id:
        raise RuntimeError(
            "El endpoint de creacion de conversacion no devolvio conversation_id"
        )
    return data


def send_conversation_message(conversation_id, message, trace=None):
    conversation_id = safe_str(conversation_id).strip()
    if not conversation_id:
        raise RuntimeError("conversation_id vacio al enviar mensaje")

    url = f"{_base_url()}/api/v1/conversations/{conversation_id}/"
    payload = {
        "trace": trace or {},
        "message": safe_str(message),
    }

    t0 = datetime.now()
    response = requests.post(
        url,
        json=payload,
        headers=_headers(json_content=True),
        timeout=TEXT_SUMMARIZER_TIMEOUT,
        verify=TEXT_SUMMARIZER_VERIFY_SSL,
    )
    latency_s = round((datetime.now() - t0).total_seconds(), 2)
    response.raise_for_status()

    try:
        data = response.json()
    except ValueError:
        data = response.text

    return AgentResponse(
        text=_extract_text(data),
        latency_s=latency_s,
        exit_status=_extract_exit_status(data),
        raw=data,
    )


def upload_document(file_path):
    file_path = safe_str(file_path).strip()
    if not file_path:
        return None

    path = Path(file_path)
    if not path.exists():
        raise RuntimeError(f"No existe el archivo document_path: {file_path}")

    url = f"{_base_url()}/api/v1/documents/"
    form_data = {
        "force_text_extraction": (
            "true" if TEXT_SUMMARIZER_FORCE_TEXT_EXTRACTION else "false"
        )
    }

    with path.open("rb") as file:
        files = {
            "file": (path.name, file, "application/pdf"),
        }
        response = requests.post(
            url,
            headers=_headers(json_content=False),
            files=files,
            data=form_data,
            timeout=TEXT_SUMMARIZER_TIMEOUT,
            verify=TEXT_SUMMARIZER_VERIFY_SSL,
        )

    response.raise_for_status()
    try:
        return response.json()
    except ValueError:
        return {"raw_response": response.text}

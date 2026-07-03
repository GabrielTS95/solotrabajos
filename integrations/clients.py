import threading
from datetime import datetime

import httpx
import requests
from openai import AzureOpenAI

from config import (
    API_KEY,
    AZURE_OPENAI_API_KEY,
    AZURE_OPENAI_API_VERSION,
    AZURE_OPENAI_ENDPOINT,
    CUSTOMER_PROC_URL,
    DEBUG_HTTP,
    URL_CHAT,
)
from core.utils import format_chat_id_log, safe_str

_thread_local = threading.local()

def obtener_http_client():
    thread_http_client = getattr(_thread_local, "http_client", None)
    if thread_http_client is None:
        thread_http_client = httpx.Client(verify=False)
        _thread_local.http_client = thread_http_client
    return thread_http_client


def obtener_cliente_azure():
    thread_client = getattr(_thread_local, "azure_client", None)
    if thread_client is None:
        thread_client = AzureOpenAI(
            api_key=AZURE_OPENAI_API_KEY,
            azure_endpoint=AZURE_OPENAI_ENDPOINT,
            api_version=AZURE_OPENAI_API_VERSION,
            http_client=obtener_http_client(),
        )
        _thread_local.azure_client = thread_client
    return thread_client

def create_chat_and_headers(request_cliente_json):
    print("CONECTANDOME CON EL AGENTE DE PHOENIX")
    # payload_create = {"user_id": user_id, "initial_message": mensaje_inicio}
    headers_create = {"X-API-key": API_KEY, "Content-Type": "application/json"}

    r1 = requests.post(
        URL_CHAT,
        json=request_cliente_json,
        headers=headers_create,
        timeout=600,
        verify=False,
    )
    # print(r1.json)
    r1.raise_for_status()
    resp_create = r1.json()
    chat_id = resp_create.get("chat", {}).get("id")
    token = resp_create.get("token")
    user_id = resp_create.get("chat", {}).get("user_id")
    if not chat_id or not token:
        raise RuntimeError(f"No se obtuvo chat_id/token. Resp: {resp_create}")
    print(format_chat_id_log(chat_id))
    url_msg = f"{URL_CHAT}/{chat_id}/messages?user_id={user_id}"
    headers_msg = {
        "X-API-key": API_KEY,
        "X-Agent-Token": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    print(f"URL mensajes: {url_msg}")
    return chat_id, url_msg, headers_msg


# ======================================================================================================================
# METODO PARA CONECTARSE CON EL AGENTE DE PHOENIX
# ======================================================================================================================


def _post_customer_proc(correct_payload, headers_create):
    response = requests.post(
        CUSTOMER_PROC_URL,
        json=correct_payload,
        headers=headers_create,
        timeout=600,
        verify=False,
    )

    response.raise_for_status()
    return response


def add_new_cic_to_customer_proc(request_cliente_json):
    print("INSERTANDO NUEVOS REGISTROS EN DH_CUSTOMER_PROC")
    headers_create = {"X-API-key": API_KEY, "Content-Type": "application/json"}
    payload = {
        "_id": request_cliente_json["customer_data"]["cic"],
        "user_name": request_cliente_json["customer_data"]["user_name"],
        "dni": request_cliente_json["customer_data"]["dni"],
        "phone": request_cliente_json["customer_data"]["phone"],
        "cic": request_cliente_json["customer_data"]["cic"],
        "segments": request_cliente_json["customer_data"]["segments"],
        "classification": request_cliente_json["customer_data"]["classification"],
        "val_debt_amount_1": request_cliente_json["customer_data"]["val_debt_amount_1"],
        "val_currency1": request_cliente_json["customer_data"]["val_currency1"],
        "account_number_1": request_cliente_json["customer_data"]["account_number_1"],
        "val_debt_amount_2": request_cliente_json["customer_data"]["val_debt_amount_2"],
        "val_currency2": request_cliente_json["customer_data"]["val_currency2"],
        "account_number_2": request_cliente_json["customer_data"]["account_number_2"],
        "qty_overdue_days": request_cliente_json["customer_data"]["qty_overdue_days"],
        "product": request_cliente_json["customer_data"]["product"],
        "last_pdp": request_cliente_json["customer_data"]["last_pdp"],
        "active_pkg": request_cliente_json["customer_data"]["active_pkg"],
        "client_statement_raw": request_cliente_json["customer_data"][
            "client_statement_raw"
        ],
        "profile_quadrant": request_cliente_json["customer_data"]["profile_quadrant"],
        "cod_customer_priority": request_cliente_json["customer_data"][
            "cod_customer_priority"
        ],
        "customer_type": request_cliente_json["customer_data"]["customer_type"],
    }
    correct_payload = {"items": [payload]}
    cic = payload["cic"]

    def _insert_once():
        response = _post_customer_proc(correct_payload, headers_create)
        print(f"[DH_CUSTOMER_PROC] cic={cic} status={response.status_code}")
        print("Response body:", response.text)

    _insert_once()

def send_bot_message(url_msg, headers_msg, message):
    payload_msg = {"message": message}
    if DEBUG_HTTP:
        print("--- DEBUG SEND BOT MESSAGE ---")
        print("URL:", url_msg)
        print("MESSAGE_LEN:", len(safe_str(message)))
    t0 = datetime.now()
    r = requests.post(
        url_msg, json=payload_msg, headers=headers_msg, timeout=600, verify=False
    )
    latency_s = round((datetime.now() - t0).total_seconds(), 2)
    r.raise_for_status()
    data = r.json()
    bot_text = data.get("content", "")
    exit_status = 0
    try:
        exit_status = int(
            data.get("metadata", {}).get("outputs", {}).get("exit_status", 0)
        )
    except Exception:
        exit_status = 0
    return safe_str(bot_text), latency_s, exit_status, data

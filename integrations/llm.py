import threading

import httpx
from openai import AzureOpenAI

from config import (
    AZURE_OPENAI_API_KEY,
    AZURE_OPENAI_API_VERSION,
    AZURE_OPENAI_ENDPOINT,
)

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

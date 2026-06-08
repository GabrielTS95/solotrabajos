import os
import json
import html
import requests
import threading
import time
import pandas as pd
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
from datetime import datetime
from openai import AzureOpenAI
import httpx
from faker import Faker
from datetime import timedelta

_thread_local = threading.local()
_customer_proc_lock = threading.Lock()


def _get_env_int(name, default):
    try:
        return int(os.getenv(name, str(default)))
    except (TypeError, ValueError):
        return default


def _get_env_float(name, default):
    try:
        return float(os.getenv(name, str(default)))
    except (TypeError, ValueError):
        return default

http_client = httpx.Client(verify=False)  # cliente global usado al iniciar el script

# ======================================================================================================================
# CONFIGURACIÓN LOCAL
# ======================================================================================================================
AZURE_OPENAI_API_KEY = os.getenv(
    "AZURE_OPENAI_API_KEY",
    "",
)
AZURE_OPENAI_ENDPOINT = os.getenv(
    "AZURE_OPENAI_ENDPOINT",
    "https://aaifaiaseu2d01.openai.azure.com",
)
AZURE_OPENAI_API_VERSION = os.getenv(
    "AZURE_OPENAI_API_VERSION",
    "2024-05-01-preview",
)

# En Azure OpenAI, model=deployment name
MODEL_NAME = "gpt-4.1"
#API_KEY = os.getenv("BOT_API_KEY", "w46582eb-1f41-455e-1f4c-3b17d7f5a0f3")
API_KEY = os.getenv("BOT_API_KEY", "cde")

MAX_TURNS_SAFE = 15
MAX_WORKERS_DEFAULT = 20
#URL_CHAT = "https://wapceu2ainac01.azurewebsites.net/api/v1/chats"
URL_CHAT = "https://wapceu2ainad01.azurewebsites.net/api/v1/chats"

CUSTOMER_PROC_URL = os.getenv(
    "CUSTOMER_PROC_URL",
    #"https://fncteu2ainac02.azurewebsites.net/api/setcicinputs",
    "https://fncteu2ainad02.azurewebsites.net/api/setcicinputs",

)
CUSTOMER_PROC_MAX_RETRIES = max(1, _get_env_int("CUSTOMER_PROC_MAX_RETRIES", 5))
CUSTOMER_PROC_RETRY_BACKOFF_S = max(
    0.0, _get_env_float("CUSTOMER_PROC_RETRY_BACKOFF_S", 0.0)
)
CUSTOMER_PROC_SETTLE_DELAY_S = max(
    0.0, _get_env_float("CUSTOMER_PROC_SETTLE_DELAY_S", 0.0)
)
SERIALIZE_CUSTOMER_PROC_WRITES = os.getenv(
    "SERIALIZE_CUSTOMER_PROC_WRITES", "1"
).strip().lower() in {"1", "true", "yes", "y", "si"}
CUSTOMER_PROC_RETRYABLE_STATUS = {408, 425, 429, 500, 502, 503, 504}
BASE_TURN_DELAY_S = max(0.0, _get_env_float("BASE_TURN_DELAY_S", 0.0))
PDP_CONFORMIDAD_DELAY_S = max(0.0, _get_env_float("PDP_CONFORMIDAD_DELAY_S", 0.0))
CLIENT_MESSAGE_DELAY_S = max(0.0, _get_env_float("CLIENT_MESSAGE_DELAY_S", 0.0))
PARALLEL_PROGRESS_LOG_EVERY_S = max(
    1.0, _get_env_float("PARALLEL_PROGRESS_LOG_EVERY_S", 30.0)
)
PARALLEL_GLOBAL_TIMEOUT_S = max(0.0, _get_env_float("PARALLEL_GLOBAL_TIMEOUT_S", 0.0))

CSV_PATH = os.getenv(
    "CSV_PATH", r"D:\Datos de Usuarios\T76960\Squad Phoenix\auto-phoenix\auto_pruebas_automatizadas\desa_pruebas_tempranas.csv",
)

# RUN_LLM_JUDGE = os.getenv("RUN_LLM_JUDGE", "1").strip().lower() in {
#     "1",
#     "true",
#     "yes",
#     "y",
#     "si",
# }

CSV_SEP = ";"
OUTPUT_DIR = os.getenv("OUTPUT_DIR", "./reportes")
os.makedirs(OUTPUT_DIR, exist_ok=True)
# ======================================================================================================================
# CLIENTE AZURE OPENAI
# ======================================================================================================================
client = AzureOpenAI(
    api_key=AZURE_OPENAI_API_KEY,
    azure_endpoint=AZURE_OPENAI_ENDPOINT,
    api_version=AZURE_OPENAI_API_VERSION,
    http_client=http_client,  # <--- ¡Aquí va!clear
)


def obtener_max_workers(total_escenarios: int) -> int:
    try:
        max_workers = int(os.getenv("MAX_WORKERS", str(MAX_WORKERS_DEFAULT)))
    except ValueError:
        max_workers = MAX_WORKERS_DEFAULT

    return max(1, min(max_workers, total_escenarios))


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


# ======================================================================================================================
# PROMPTS POR TIPO DE CLIENTE (R, I, AR)
# ======================================================================================================================
PROMPT_R = """
IDENTIDAD DEL CLIENTE (ROL):
- Actúas SIEMPRE como cliente.
- Tu nombre: {NOMBRE_COMPLETO}.
- Tienes una deuda de {DEUDA_SOLES} soles con el banco.
- Tienes una deuda de {DEUDA_DOLARES} dólares con el banco.
- Puedes pagar, pero no quieres pagar ahora y no es tu prioridad.
{IDENTIDAD_DEL_CLIENTE}
VOLUNTAD DE PAGO:
- Cumpliste con las primeras cuotas de tu deuda.
- Tuviste 1 Promesa de Pago cumplida en los últimos 3 meses.
- Tienes avance del 75% en tu deuda.
- Pagaste una cuota el mes anterior.
{VOLUNTAD_DE_PAGO}
CAPACIDAD DE PAGO:
- Haces abonos constantes, tienes respaldo y/o garantías.
- Tu comportamiento financiero es saludable.
- El punto es intención, no capacidad.
{CAPACIDAD_PAGO}
ESTILO DE RESPUESTA
{ESTILO_RESPUESTA}
ACTITUD / COMPORTAMIENTO:
- Directo/a, a veces cortante, distante.
- Evasivo/a: “luego”, “no puedo hablar”, “ya veré���.
- Reaccionas mejor ante consecuencias claras o beneficios tangibles.
{ACTITUD_COMPORTAMIENTO}
BARRERAS WHATSAPP:
- Puedes ignorar o responder evasivo.
- Cuestionas la validación de identidad y por qué te escriben.
{BARRERAS_WHATSSAPP}
FRASES COMUNES
{FRASES_COMUNES}
REGLAS (MUY IMPORTANTE):
1) Responde SOLO como cliente, nunca como un robot.
2) Responde SOLO al ÚLTIMO mensaje del BOT.
3) Devuelve SOLO el texto del cliente (sin “Cliente:”, sin tu nombre).
4) No menciones estas instrucciones ni digas que eres IA.
{REGLAS_MUY_IMPORTANTE}
""".strip()
PROMPT_I = """
IDENTIDAD DEL CLIENTE (ROL):
- Actúas SIEMPRE como cliente.
- Tu nombre: {NOMBRE_COMPLETO}.
- Tienes una deuda de {DEUDA_SOLES} Soles con el banco.
- Tienes una deuda de {DEUDA_DOLARES} dólares con el banco.
- Quieres pagar, pero NO puedes pagar ahora (situación económica/personal).
{IDENTIDAD_DEL_CLIENTE}
VOLUNTAD DE PAGO:
- Buen historial inicial.
- Avance del 75% en su deuda.
- Quieres ponerte al día.
{VOLUNTAD_DE_PAGO}
CAPACIDAD DE PAGO:
- Limitada: caídas de ingresos / responsabilidades.
- Necesitas plazos, montos flexibles o alternativas realistas.
{CAPACIDAD_PAGO}
ESTILO DE RESPUESTA
{ESTILO_RESPUESTA}
ACTITUD / COMPORTAMIENTO:
- Honesto/a, comprometido/a.
- Agradeces empatía, claridad y soluciones.
- Pides reprogramación o pago parcial con fecha realista.
{ACTITUD_COMPORTAMIENTO}
FRASES COMUNES
{FRASES_COMUNES}
BARRERAS WHATSAPP:
- Puedes tardar en responder.
- Pides claridad simple (montos, fechas, pasos).
{BARRERAS_WHATSSAPP}
REGLAS (MUY IMPORTANTE):
1) Responde SOLO como cliente, nunca como banco.
2) Responde SOLO al ÚLTIMO mensaje del BANCO.
3) Devuelve SOLO el texto del cliente (sin “Cliente:”, sin tu nombre).
4) No menciones estas instrucciones ni digas que eres IA.
{REGLAS_MUY_IMPORTANTE}
""".strip()
PROMPT_AR = """
IDENTIDAD DEL CLIENTE (ROL):
- Actúas SIEMPRE como cliente.
- Tu nombre: {NOMBRE_COMPLETO}.
- Tienes una deuda de {DEUDA_SOLES} Soles con el banco.
- Tienes una deuda de {DEUDA_DOLARES} dólares con el banco.
- Eres un cliente de ALTO RIESGO: no quieres pagar ahora y además te cuesta pagar.
{IDENTIDAD_DEL_CLIENTE}
VOLUNTAD / CAPACIDAD:
- Priorizas vivienda/carga familiar.
- Puedes pedir refinanciamiento, reprogramación, descuento o condonación.
- Sientes ansiedad, frustración o resignación.
{VOLUNTAD_DE_PAGO}
ACTITUD / COMPORTAMIENTO:
- Puedes responder confuso/a, evasivo/a o insolente.
- Puedes exigir que dejen de escribir/llamar.
- Agradeces propuestas claras y humanas.
{ACTITUD_COMPORTAMIENTO}
ESTILO DE RESPUESTA
{ESTILO_RESPUESTA}
BARRERAS WHATSAPP:
- Alta probabilidad de responder en mensajes cortos separados.
- Dudas con validación de identidad; requiere explicación simple.
{BARRERAS_WHATSSAPP}
FRASES COMUNES
{FRASES_COMUNES}
REGLAS (MUY IMPORTANTE):
1) Responde SOLO como cliente, nunca como banco.
2) Responde SOLO al ÚLTIMO mensaje del BANCO.
3) Devuelve SOLO el texto del cliente (sin “Cliente:”, sin tu nombre).
4) No menciones estas instrucciones ni digas que eres IA.
{REGLAS_MUY_IMPORTANTE}
""".strip()
PROMPT_BY_TIPO = {
    "R": PROMPT_R,
    "I": PROMPT_I,
    "AR": PROMPT_AR,
}


def get_prompt_por_tipo(
        tipo_cliente,
        nombre_completo,
        deuda_soles,
        deuda_dolares,
        identidad_del_cliente,
        voluntad_de_pago,
        capacidad_pago,
        estilo_respuesta,
        actitud_comportamiento,
        barreras_whatssapp,
        frases_comunes,
        reglas_muy_importante,
):
    tipo = (tipo_cliente or "").strip().upper()
    template = PROMPT_BY_TIPO.get(tipo, PROMPT_R)
    return template.format(
        NOMBRE_COMPLETO=nombre_completo or "",
        DEUDA_SOLES=deuda_soles or "",
        DEUDA_DOLARES=deuda_dolares or "",
        IDENTIDAD_DEL_CLIENTE=identidad_del_cliente or "",
        VOLUNTAD_DE_PAGO=voluntad_de_pago or "",
        CAPACIDAD_PAGO=capacidad_pago or "",
        ESTILO_RESPUESTA=estilo_respuesta or "",
        ACTITUD_COMPORTAMIENTO=actitud_comportamiento or "",
        BARRERAS_WHATSSAPP=barreras_whatssapp or "",
        FRASES_COMUNES=frases_comunes or "",
        REGLAS_MUY_IMPORTANTE=reglas_muy_importante or "",
    )


# ======================================================================================================================
# HELPERS
# ======================================================================================================================


total_exec_time = timedelta(0)  # para sumar el tiempo total de todos los escenarios


def format_td_hms(td):
    total_seconds = td.total_seconds()
    hours, remainder = divmod(int(total_seconds), 3600)
    minutes, seconds = divmod(int(total_seconds) % 3600, 60)
    sec_with_decimals = total_seconds - int(total_seconds)
    seconds_with_decimals = seconds + sec_with_decimals
    return f"{hours:02}:{minutes:02}:{seconds_with_decimals:05.2f}"


def safe_str(x):
    if x is None:
        return ""
    try:
        if pd.isna(x):
            return ""
    except Exception:
        pass
    return str(x)


def format_chat_id_log(chat_id):
    return f'{{"chat_id" : "{safe_str(chat_id)}"}}'


def build_conversation_text(historia):
    lines = []
    for rol, texto in historia:
        texto = safe_str(texto).strip()
        if not texto:
            continue
        if rol == "usuario":
            lines.append(f"CLIENTE: {texto}")
        else:
            lines.append(f"AG. PHOENIX: {texto}")
    return "\n".join(lines).strip()


def build_full_conversation(historia):
    lines = []
    for rol, texto in historia:
        prefix = "CLIENTE" if rol == "usuario" else "AG. PHOENIX"
        lines.append(f"{prefix}: {safe_str(texto)}")
    return "\n".join(lines)


def parsear_secuencia_mensajes(valor):
    texto = safe_str(valor).strip()
    if not texto:
        return []
    lineas = [linea.strip() for linea in texto.splitlines()]
    lineas = [linea for linea in lineas if linea]
    return lineas


# ======================================================================================================================
# USER SIMULATOR
# ======================================================================================================================
def llamada_user_simulator(
        prompt_cliente, historia, max_output_tokens=100, model=MODEL_NAME
):
    prompt_cliente = safe_str(prompt_cliente).strip()
    conv = build_conversation_text(historia)
    user_turn = f"""
CONVERSACIÓN HASTA AHORA:
{conv}
INSTRUCCIONES:
- Te toca responder COMO CLIENTE al ÚLTIMO mensaje del BANCO.
- Devuelve SOLO el texto del cliente (sin prefijos tipo "Cliente:", "Usuario:", etc.).
- No termines la conversación (no digas "fin"/"adiós") a menos que sea estrictamente necesario.
- Responde SIEMPRE de forma breve y solo lo necesario. No uses frases largas.
""".strip()
    resp = obtener_cliente_azure().chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": prompt_cliente},
            {"role": "user", "content": user_turn},
        ],
        max_tokens=max_output_tokens,
        temperature=0.7,
        stop=None,
    )
    return (resp.choices[0].message.content or "").strip()


# ======================================================================================================================
# LLAMAR AL JUEZ
# ======================================================================================================================


FUNCIONALIDADES_JUEZ = [
    ("persuasion_total", "Persuasión total"),
    ("persuasion_parcial", "Persuasión parcial"),
    ("motivos_no_pago", "Motivos no pago"),
    ("registro_pdp", "Registro pdp"),
    ("canales_atencion", "Canales atención"),
    ("registro_nps", "Registro nps"),
    ("derivacion_asesor", "Ofrecer asesor"),
    ("registro_cita", "Registro cita"),
    ("consecuencias_no_pago", "Consecuencias no pago"),
    ("preguntas_frecuentes", "Preguntas frecuentes"),
]

FUNCIONALIDADES_VISIBLES_REPORTE = [
    ("persuasion_total", "Persuasión total"),
    ("persuasion_parcial", "Persuasión parcial"),
    ("motivos_no_pago", "Motivos no pago"),
    ("registro_pdp", "Registro pdp"),
    ("canales_atencion", "Canales atención"),
    ("registro_nps", "Registro nps"),
    ("derivacion_asesor", "Ofrecer asesor"),
    ("registro_cita", "Registro cita"),
    ("consecuencias_no_pago", "Consecuencias no pago"),
    ("preguntas_frecuentes", "Preguntas frecuentes"),
]

def get_prompt_juez(question, perfil, caso_de_prueba="", reglas_juez=None):

    prompt = f"""
Eres un juez experto en cobranzas peruanas y en evaluación de agentes virtuales del Banco de Crédito del Perú (BCP).

Tu objetivo es evaluar una conversación de cobranza y medir el cumplimiento del agente respecto a las FUNCIONALIDADES definidas.
Debes devolver EXCLUSIVAMENTE un objeto JSON válido que cumpla estrictamente con el JSON Schema provisto.

==============================
CRITERIO DE EVALUACIÓN GENERAL
==============================
Para cada funcionalidad asigna un score entero:
-  1 → APLICA y el agente CUMPLE todas las reglas.
-  0 → APLICA y el agente NO CUMPLE (solo si existía obligación real).
- -1 → NO APLICA (la funcionalidad nunca se activó).

IMPORTANTE:
- NO CUMPLE (0) significa que el agente falló en algo que estaba obligado a hacer.
- NO APLICA (-1) significa que la situación nunca exigió esa funcionalidad.
- Nunca confundas “hubo interacción” con “hubo obligación”.

JUSTIFICACIÓN:
- Cita frases textuales exactas del agente o cliente.
- Si marcas 0, explica qué regla se violó y dónde.
- Si marcas -1, explica por qué no se activó la necesidad.

==============================
PERFIL DEL CLIENTE - CONTEXTO
==============================
El perfil del caso a evaluar es: {perfil}

==============================
PASO 1: EXTRAER HITOS (SOLO SI / NO, SIN INFERIR)
==============================
Antes de evaluar funcionalidades, identifica únicamente señales explícitas:
A) El cliente pidió un asesor humano (ej. “quiero un asesor”, “llámame”, “hablar con alguien”).
B) Hubo propuesta de pago con MONTO explícito (número en soles o dólares, por el agente o el cliente).
C) Hubo FECHA explícita concreta (ej. “21 de mayo”, “viernes 15”; “mañana”).
D) Hubo HORA explícita concreta (solo relevante para citas).
E) El agente afirmó explícitamente que REGISTRÓ un compromiso (ej. “queda registrado”, “he registrado tu compromiso”).
F) El agente informó medios de pago (Banca Móvil, web VíaBCP, Agentes, Agencias).
G) El agente pidió NPS y el cliente respondió con un entero 0-10 válido.
H) El caso terminó sin acuerdo (no PDP y no cita) y el agente cerró mencionando consecuencias en tono no intimidante.
I) El cliente hizo una pregunta informativa (canales, proceso, números) y el agente respondió o derivó correctamente y reencauzó.

Usa estas señales para decidir APLICA/NO APLICA en cada funcionalidad.

==============================
FUNCIONALIDADES A EVALUAR
==============================

FUNCIONALIDAD: persuasion_total
Propósito: Solicitar una promesa de pago con monto total o monto total en partes entendiendo contexto del cliente.

APLICA SI:
- El agente solicita un pago con monto total, O
- El agente solicita un pago con monto total en partes.
NO APLICA SI:
- El cliente pide asesor humano ANTES de permitir ofrecer opciones.

Reglas:
- Agente debe solicitar un pago con monto total, O
- Agente debe solicitar un pago con monto total en partes, PERO el objetivo es monto total.

------------------------------------------------

FUNCIONALIDAD: persuasion_parcial
Propósito: Solicitar una promesa de pago parcial entendiendo contexto del cliente.

APLICA SI (evidencia explícita):
- El agente solicita un pago con monto parcial, O
- El agente solicita un pago con monto objetivo por perfil (perfil 3→30%, perfil 2→20%, otro→10%), O
- El agente solicita un pago con monto mínimo aceptable (≥10% de deuda vencida).
NO APLICA SI:
- El cliente pide asesor humano ANTES de permitir ofrecer opciones.

Reglas:
- Agente debe solicitar opciones de pago parcial, Y
- Agente debe solicitar montos por perfil: perfil 3→30%, perfil 2→20%, otro→10%, Y
- Agente debe solicitar como último recurso aceptable: mínimo 10%.

------------------------------------------------

FUNCIONALIDAD: motivos_no_pago
Propósito: Solicitar motivo de no pago cuando el cliente rechaza el primer intento.

APLICA SI:
- El agente pregunta explícitamente por el motivo de no pago actual tras un rechazo inicial del cliente.
NO APLICA SI:
- El cliente acepta pagar o propone monto/fecha sin rechazo inicial, o se deriva a asesor antes.

Flujo mínimo:
1) Agente debe preguntar motivo de no pago actual.
2) Si no hay motivo específico, agente debe preguntar por PDP anterior si tiene o mencionar el motivo de no pago pasado si no tiene PDP anterior.
3) Luego retomar persuasión (ofrecer alternativa).

------------------------------------------------

FUNCIONALIDAD: registro_pdp
Propósito: Registrar formalmente la promesa de pago.

APLICA SI (todas deben cumplirse):
- El cliente ACEPTA explícitamente un monto (número) Y una fecha concreta, Y
- El agente afirma explícitamente que REGISTRA el compromiso.

NO APLICA SI:
- El cliente nunca acepta monto y fecha, aunque el agente lo haya propuesto, O
- El cliente rechaza o evita confirmar el compromiso, O
- El agente solo ofrece “puedo registrar”, “podría registrar”, “cuando quieras registramos”, O
- El cliente solicitó derivación con asesor.

Reglas:
- Debe existir aceptación explícita del cliente (monto + fecha).
- El agente debe afirmar registro exitoso.
- El agente debe reforzar medios de pago tras el registro.

------------------------------------------------

FUNCIONALIDAD: canales_atencion
Propósito: Informar canales y horario cuando el cliente lo solicita.

APLICA SI:
- El cliente pregunta explícitamente por canales, teléfono, horario, atención, asesor o llamada.

NO APLICA SI:
- El cliente nunca hizo una consulta sobre canales,
  aunque el agente los haya mencionado proactivamente.

Regla:
- Evaluar solo si responde correctamente a una pregunta del cliente.

------------------------------------------------

FUNCIONALIDAD: registro_nps
Propósito: Registro de NPS cuando el cliente responde.

APLICA SI (todas deben cumplirse):
- Hubo registro exitoso de PDP O de cita, Y
- El agente debe pedir NPS.

NO APLICA SI:
- Nunca hubo registro de PDP ni de cita.
- El cliente se mostró reacio o terminó la conversación sin acuerdo.

Reglas:
- Pedir un entero 0-10.
- Reintentar SOLO por formato inválido.
- Si el cliente se niega, no insistir.

------------------------------------------------

FUNCIONALIDAD: derivacion_asesor
Propósito: Escalar cuando no hay acuerdo o el cliente solicita atención humana.

APLICA SI:
- El cliente pide asesor humano explícitamente, O
- El agente y el cliente no llegan a ningún acuerdo de pago ni de cita, entonces el agente debe ofrecer derivación a asesor.
NO APLICA SI:
- Hay un ACUERDO DE ACEPTACIÓN de compromiso de pago con monto y fecha explicitos, entre el agente y el cliente (si o si debe haber acuerdo explícito).

Regla:
- Agente debe ofrecer derivación (inmediata o agendada) de forma clara.

------------------------------------------------

FUNCIONALIDAD: registro_cita
Propósito: Registro de una cita con asesor cuando el cliente acepta o solicita.

APLICA SI (todas deben cumplirse):
- El cliente acepta explícitamente agendar, Y
- Existe fecha Y hora concretas, Y
- El agente confirma que la cita fue registrada.

NO APLICA SI:
- El cliente rechaza la cita, O
- El agente solo ofrece agendar pero no hay aceptación, O
- No existe fecha y hora explícitas, O
- Hay un acuerdo explícito de compromiso de pago con monto y fecha.

Reglas:
- Ofrecer cita ≠ registrar cita.
- Sin aceptación explícita del cliente, siempre marca NO APLICA (-1).

------------------------------------------------

FUNCIONALIDAD: consecuencias_no_pago
Propósito: Cerrar correctamente con clientes muy reacios.

APLICA SI:
- El cliente y el agente no llegan a ningún acuerdo de pago ni de cita ni acepta asesor.

NO APLICA SI:
- Hubo acuerdo de PDP.
- Hubo acuerdo de cita.

Regla:
- Mencionar consecuencias SOLO como último recurso.

------------------------------------------------

FUNCIONALIDAD: preguntas_frecuentes
Propósito: Atender consultas informativas y reencauzar.

APLICA SI:
- El cliente hace una pregunta informativa
  (canales, proceso, números, horarios).

NO APLICA SI:
- El cliente solo expresa dificultad de pago o pide alternativas.
- La interacción es puramente de negociación.

Reglas:
- Responder o derivar.
- Luego reencauzar a resolver la deuda.

==============================
OUTPUT
==============================
Devuelve exclusivamente un JSON válido conforme al schema.
Cada funcionalidad debe tener:
- <nombre_funcionalidad>_score
- <nombre_funcionalidad>_justification

schema:
  type: object
  additionalProperties: false
  required:
    - persuasion_total_score
    - persuasion_total_justification
    - persuasion_parcial_score
    - persuasion_parcial_justification
    - motivos_no_pago_score
    - motivos_no_pago_justification
    - registro_pdp_score
    - registro_pdp_justification
    - canales_atencion_score
    - canales_atencion_justification
    - registro_nps_score
    - registro_nps_justification
    - derivacion_asesor_score
    - derivacion_asesor_justification
    - registro_cita_score
    - registro_cita_justification
    - consecuencias_no_pago_score
    - consecuencias_no_pago_justification
    - preguntas_frecuentes_score
    - preguntas_frecuentes_justification

  properties:

    persuasion_total_score:
    type: integer
    enum: [-1, 0, 1]

    persuasion_total_justification:
    type: string

    persuasion_parcial_score:
    type: integer
    enum: [-1, 0, 1]

    persuasion_parcial_justification:
    type: string

    motivos_no_pago_score:
    type: integer
    enum: [-1, 0, 1]

    motivos_no_pago_justification:
    type: string

    registro_pdp_score:
    type: integer
    enum: [-1, 0, 1]

    registro_pdp_justification:
    type: string

    canales_atencion_score:
    type: integer
    enum: [-1, 0, 1]

    canales_atencion_justification:
    type: string

    registro_nps_score:
    type: integer
    enum: [-1, 0, 1]

    registro_nps_justification:
    type: string

    derivacion_asesor_score:
    type: integer
    enum: [-1, 0, 1]

    derivacion_asesor_justification:
    type: string

    registro_cita_score:
    type: integer
    enum: [-1, 0, 1]

    registro_cita_justification:
    type: string

    consecuencias_no_pago_score:
    type: integer
    enum: [-1, 0, 1]

    consecuencias_no_pago_justification:
    type: string

    preguntas_frecuentes_score:
    type: integer
    enum: [-1, 0, 1]

    preguntas_frecuentes_justification:
    type: string

No expliques nada fuera del JSON.

CONVERSACIÓN A EVALUAR:
{question}
"""
    contexto_fecha_base = construir_contexto_fecha_base_juez_metricas()
    prompt += f"""

==============================
EVALUACION METRICAS ADICIONAL
==============================
Adicionalmente, evalua esta misma conversación en métricas de calidad conversacional.

CASO DE PRUEBA:
{caso_de_prueba or 'Sin caso de prueba definido.'}

REGLAS DEL JUEZ:
{reglas_juez or 'Sin reglas para este caso.'}

FECHA BASE PARA EVALUAR FECHAS RELATIVAS:
{contexto_fecha_base}

Metricas obligatorias:
- coherencia
- fluidez
- cumplimiento
- integridad
- claridad
- correccion

Reglas obligatorias:
- Para la métrica CUMPLIMIENTO debes evaluar principalmente si el agente logró o no lo que se pide validar en el CASO DE PRUEBA.
- Si el agente contradice, omite o no alcanza el objetivo del CASO DE PRUEBA, el puntaje de cumplimiento debe bajar.
- Si el CASO DE PRUEBA valida interpretación de fechas relativas, debes evaluar estrictamente expresiones como "mañana", "pasado mañana", "la próxima semana", "este lunes" o "el próximo martes" usando la FECHA BASE indicada arriba.
- Si el agente convierte mal una fecha relativa, cumplimiento debe ser <= 0.40.
- Si el agente contradice la fecha relativa del cliente, coherencia debe ser <= 0.60.
- Si el agente no valida una fecha ambigua o una fecha que no está dentro de las opciones disponibles, integridad debe ser <= 0.70.
- Si el mensaje puede confundir al cliente sobre la fecha real de la cita, claridad debe ser <= 0.70.
- Cada métrica debe estar entre 0.00 y 1.00.
- score_total debe ser igual al puntaje de cumplimiento.
- resultado = "FAIL" si cumplimiento está entre 0.00 y 0.49.
- resultado = "WARNING" si cumplimiento está entre 0.50 y 0.79.
- resultado = "PASS" si cumplimiento está entre 0.80 y 1.00.

IMPORTANTE FINAL:
- Ignora cualquier formato de salida previo definido arriba.
- Devuelve SOLO un JSON válido con esta estructura exacta:
{{
    "funcionalidades": {{
        "persuasion_total_score": -1,
        "persuasion_total_justification": "texto",
        "persuasion_parcial_score": -1,
        "persuasion_parcial_justification": "texto",
        "motivos_no_pago_score": -1,
        "motivos_no_pago_justification": "texto",
        "registro_pdp_score": -1,
        "registro_pdp_justification": "texto",
        "canales_atencion_score": -1,
        "canales_atencion_justification": "texto",
        "registro_nps_score": -1,
        "registro_nps_justification": "texto",
        "derivacion_asesor_score": -1,
        "derivacion_asesor_justification": "texto",
        "registro_cita_score": -1,
        "registro_cita_justification": "texto",
        "consecuencias_no_pago_score": -1,
        "consecuencias_no_pago_justification": "texto",
        "preguntas_frecuentes_score": -1,
        "preguntas_frecuentes_justification": "texto"
    }},
    "metricas": {{
        "coherencia": 0.00,
        "exp_coherencia": "texto breve",
        "fluidez": 0.00,
        "exp_fluidez": "texto breve",
        "cumplimiento": 0.00,
        "exp_cumplimiento": "texto breve",
        "integridad": 0.00,
        "exp_integridad": "texto breve",
        "claridad": 0.00,
        "exp_claridad": "texto breve",
        "correccion": 0.00,
        "exp_correccion": "texto breve",
        "score_total": 0.00,
        "resultado": "FAIL",
        "justificacion": "resumen general breve"
    }}
}}
"""
    return prompt.strip()



def normalizar_score_funcionalidad(value):
    """
    Convierte cualquier valor del juez a -1, 0 o 1.
    -1 = NO APLICA
     0 = NO CUMPLE
     1 = CUMPLE
    """
    try:
        score = int(value)
        if score in [-1, 0, 1]:
            return score
        return 0
    except Exception:
        return 0


def calcular_resumen_funcionalidades(result):
    scores = []

    for key, _ in FUNCIONALIDADES_VISIBLES_REPORTE:
        scores.append(result.get(f"{key}_score", 0))

    total_no_aplica = sum(1 for s in scores if s == -1)
    total_cumple = sum(1 for s in scores if s == 1)
    total_no_cumple = sum(1 for s in scores if s == 0)

    scores_aplicables = [s for s in scores if s != -1]

    if scores_aplicables:
        score_total = round(total_cumple / len(scores_aplicables), 2)
    else:
        score_total = 1.00

    resultado = "PASS" if score_total >= 0.80 else "FAIL"

    justificacion = (
        f"Funcionalidades aplicables evaluadas: {len(scores_aplicables)}. "
        f"Cumple: {total_cumple}. "
        f"No cumple: {total_no_cumple}. "
        f"No aplica: {total_no_aplica}. "
        f"Score calculado solo sobre funcionalidades aplicables."
    )

    result["total_cumple"] = total_cumple
    result["total_no_cumple"] = total_no_cumple
    result["total_no_aplica"] = total_no_aplica
    result["total_aplicables"] = len(scores_aplicables)
    result["score_total"] = score_total
    result["resultado"] = resultado
    result["justificacion"] = justificacion

    return result


def build_error_juez_result(motivo, raw_json="", latency_s=0.0):
    result = {}

    for key, _ in FUNCIONALIDADES_JUEZ:
        result[f"{key}_score"] = 0
        result[f"{key}_justification"] = (
            f"No se pudo evaluar esta funcionalidad. {motivo}"
        )

    result["raw_json"] = raw_json or "{}"
    result["latencia_eval_s"] = latency_s

    return calcular_resumen_funcionalidades(result)


def _normalizar_score_01(value):
    try:
        score = float(value)
        if score < 0:
            return 0.0
        if score > 1:
            return 1.0
        return round(score, 2)
    except Exception:
        return 0.0


def clasificar_cumplimiento_metricas(score):
    score = _normalizar_score_01(score)
    if score <= 0.49:
        return "FAIL"
    if score <= 0.79:
        return "WARNING"
    if score <= 1.00:
        return "PASS"


DIAS_SEMANA_ES = [
    "lunes",
    "martes",
    "miércoles",
    "jueves",
    "viernes",
    "sábado",
    "domingo",
]

MESES_ES = [
    "enero",
    "febrero",
    "marzo",
    "abril",
    "mayo",
    "junio",
    "julio",
    "agosto",
    "septiembre",
    "octubre",
    "noviembre",
    "diciembre",
]


def formatear_fecha_juez_metricas(fecha):
    return (
        f"{DIAS_SEMANA_ES[fecha.weekday()]} {fecha.day:02d} "
        f"de {MESES_ES[fecha.month - 1]} de {fecha.year} "
        f"({fecha.strftime('%Y-%m-%d')})"
    )


def construir_contexto_fecha_base_juez_metricas():
    fecha_base = datetime.now()
    manana = fecha_base + timedelta(days=1)
    pasado_manana = fecha_base + timedelta(days=2)
    dias_hasta_proximo_lunes = (7 - fecha_base.weekday()) % 7 or 7
    proximo_lunes = fecha_base + timedelta(days=dias_hasta_proximo_lunes)
    proximo_domingo = proximo_lunes + timedelta(days=6)

    return (
        f"Fecha base actual: {formatear_fecha_juez_metricas(fecha_base)}.\n"
        f'Equivalencia obligatoria: "mañana" = {formatear_fecha_juez_metricas(manana)}.\n'
        f'Equivalencia obligatoria: "pasado mañana" = {formatear_fecha_juez_metricas(pasado_manana)}.\n'
        f'Equivalencia obligatoria: "la próxima semana" = del {formatear_fecha_juez_metricas(proximo_lunes)} '
        f"al {formatear_fecha_juez_metricas(proximo_domingo)}."
    )


def build_error_juez_result_metricas(motivo, raw_json="", latency_s=0.0):
    return {
        "m_coherencia": 0.0,
        "exp_coherencia": "No se pudo evaluar coherencia.",
        "m_fluidez": 0.0,
        "exp_fluidez": "No se pudo evaluar fluidez.",
        "m_cumplimiento": 0.0,
        "exp_cumplimiento": "No se pudo evaluar cumplimiento.",
        "m_integridad": 0.0,
        "exp_integridad": "No se pudo evaluar integridad.",
        "m_claridad": 0.0,
        "exp_claridad": "No se pudo evaluar claridad.",
        "m_correccion": 0.0,
        "exp_correccion": "No se pudo evaluar corrección.",
        "score_total": 0.0,
        "resultado": "FAIL",
        "justificacion": motivo,
        "raw_json": raw_json or "{}",
        "latencia_eval_s": latency_s,
    }


def llm_judge_metricas(
    question: str,
    perfil: str = "",
    caso_de_prueba: str = "",
    reglas_juez: str = "",
    model=MODEL_NAME,
):
    eval_juez = build_error_juez_result("No se ejecutó el juez por funcionalidades.")

    metricas_eval = build_error_juez_result_metricas(
        "No se ejecutó el juez metrica."
    )

    eval_juez.update(
        {
            "resultado_metricas": metricas_eval.get("resultado", "FAIL"),
            "justificacion_metricas": metricas_eval.get("justificacion", ""),
            "score_total_metricas": metricas_eval.get("score_total", 0.0),
            "m_coherencia": metricas_eval.get("m_coherencia", 0.0),
            "exp_coherencia": metricas_eval.get("exp_coherencia", ""),
            "m_fluidez": metricas_eval.get("m_fluidez", 0.0),
            "exp_fluidez": metricas_eval.get("exp_fluidez", ""),
            "m_cumplimiento": metricas_eval.get("m_cumplimiento", 0.0),
            "exp_cumplimiento": metricas_eval.get("exp_cumplimiento", ""),
            "m_integridad": metricas_eval.get("m_integridad", 0.0),
            "exp_integridad": metricas_eval.get("exp_integridad", ""),
            "m_claridad": metricas_eval.get("m_claridad", 0.0),
            "exp_claridad": metricas_eval.get("exp_claridad", ""),
            "m_correccion": metricas_eval.get("m_correccion", 0.0),
            "exp_correccion": metricas_eval.get("exp_correccion", ""),
            "raw_json_metricas": metricas_eval.get("raw_json", "{}"),
            "latencia_eval_s_metricas": metricas_eval.get("latencia_eval_s", 0.0),
        }
    )

    prompt_unificado = get_prompt_juez(
        question=question,
        perfil=perfil,
        caso_de_prueba=caso_de_prueba,
        reglas_juez=reglas_juez,
    )

    marker_metricas = "==============================\nEVALUACION METRICAS ADICIONAL"
    prompt_funcionalidades = prompt_unificado.split(marker_metricas)[0].strip()

    contexto_fecha_base = construir_contexto_fecha_base_juez_metricas()
    prompt_metricas = f"""
Eres un juez experto en evaluación conversacional.

Evalúa EXCLUSIVAMENTE la calidad metrica de la conversación respecto al CASO DE PRUEBA.
No evalúes funcionalidades operativas en esta salida.

CASO DE PRUEBA:
{caso_de_prueba or 'Sin caso de prueba definido.'}

REGLAS DEL JUEZ:
{reglas_juez or 'Sin reglas para este caso.'}

FECHA BASE PARA EVALUAR FECHAS RELATIVAS:
{contexto_fecha_base}

Métricas obligatorias:
- coherencia
- fluidez
- cumplimiento
- integridad
- claridad
- correccion

Reglas:
- cumplimiento refleja qué tanto se cumplió el objetivo del CASO DE PRUEBA.
- score_total debe ser igual a cumplimiento.
- resultado = "FAIL" si cumplimiento está entre 0.00 y 0.49.
- resultado = "WARNING" si cumplimiento está entre 0.50 y 0.79.
- resultado = "PASS" si cumplimiento está entre 0.80 y 1.00.

Devuelve SOLO JSON válido con esta estructura exacta:
{{
  "coherencia": 0.00,
  "exp_coherencia": "texto breve",
  "fluidez": 0.00,
  "exp_fluidez": "texto breve",
  "cumplimiento": 0.00,
  "exp_cumplimiento": "texto breve",
  "integridad": 0.00,
  "exp_integridad": "texto breve",
  "claridad": 0.00,
  "exp_claridad": "texto breve",
  "correccion": 0.00,
  "exp_correccion": "texto breve",
  "score_total": 0.00,
  "resultado": "FAIL",
  "justificacion": "resumen general breve"
}}

CONVERSACIÓN A EVALUAR:
{question}
""".strip()

    # 1) Evalua funcionalidades en una llamada aislada
    try:
        t0_func = datetime.now()
        response_func = obtener_cliente_azure().chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "system",
                    "content": "Responde únicamente con JSON válido y sin markdown.",
                },
                {"role": "user", "content": prompt_funcionalidades},
            ],
            max_tokens=2600,
            temperature=0,
        )
        latency_func_s = round((datetime.now() - t0_func).total_seconds(), 2)
        content_func = (response_func.choices[0].message.content or "").strip()

        content_func_clean = content_func.replace("```json", "").replace("```", "").strip()
        start_func = content_func_clean.find("{")
        end_func = content_func_clean.rfind("}")
        if start_func == -1 or end_func == -1:
            raise ValueError("La respuesta de funcionalidades no contiene un JSON válido.")

        parsed_func = json.loads(content_func_clean[start_func : end_func + 1])
        if isinstance(parsed_func, dict) and isinstance(parsed_func.get("funcionalidades"), dict):
            parsed_funcionalidades = parsed_func.get("funcionalidades", {})
        else:
            parsed_funcionalidades = parsed_func if isinstance(parsed_func, dict) else {}

        result = {}
        for key, _ in FUNCIONALIDADES_JUEZ:
            score_key = f"{key}_score"
            just_key = f"{key}_justification"
            result[score_key] = normalizar_score_funcionalidad(parsed_funcionalidades.get(score_key, 0))
            result[just_key] = safe_str(parsed_funcionalidades.get(just_key, ""))

        result["raw_json"] = json.dumps(parsed_funcionalidades, ensure_ascii=False, indent=2)
        result["latencia_eval_s"] = latency_func_s
        eval_juez = calcular_resumen_funcionalidades(result)

    except Exception as e:
        eval_juez = build_error_juez_result(
            motivo=f"Error analizando salida del juez de funcionalidades: {type(e).__name__}: {e}",
            raw_json=safe_str(locals().get("content_func", "")),
            latency_s=locals().get("latency_func_s", 0.0),
        )

    # 2) Evalua metricas en una llamada independiente
    try:
        t0_clas = datetime.now()
        response_clas = obtener_cliente_azure().chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "system",
                    "content": "Responde únicamente con JSON válido y sin markdown.",
                },
                {"role": "user", "content": prompt_metricas},
            ],
            max_tokens=1600,
            temperature=0,
        )
        latency_clas_s = round((datetime.now() - t0_clas).total_seconds(), 2)
        content_clas = (response_clas.choices[0].message.content or "").strip()

        content_clas_clean = content_clas.replace("```json", "").replace("```", "").strip()
        start_clas = content_clas_clean.find("{")
        end_clas = content_clas_clean.rfind("}")
        if start_clas == -1 or end_clas == -1:
            raise ValueError("La respuesta del juez metrica no contiene un JSON válido.")

        parsed_metricas = json.loads(content_clas_clean[start_clas : end_clas + 1])
        if not isinstance(parsed_metricas, dict):
            parsed_metricas = {}

        m_cumplimiento = _normalizar_score_01(parsed_metricas.get("cumplimiento", 0))
        metricas_eval = {
            "m_coherencia": _normalizar_score_01(parsed_metricas.get("coherencia", 0)),
            "exp_coherencia": safe_str(parsed_metricas.get("exp_coherencia", "")),
            "m_fluidez": _normalizar_score_01(parsed_metricas.get("fluidez", 0)),
            "exp_fluidez": safe_str(parsed_metricas.get("exp_fluidez", "")),
            "m_cumplimiento": m_cumplimiento,
            "exp_cumplimiento": safe_str(parsed_metricas.get("exp_cumplimiento", "")),
            "m_integridad": _normalizar_score_01(parsed_metricas.get("integridad", 0)),
            "exp_integridad": safe_str(parsed_metricas.get("exp_integridad", "")),
            "m_claridad": _normalizar_score_01(parsed_metricas.get("claridad", 0)),
            "exp_claridad": safe_str(parsed_metricas.get("exp_claridad", "")),
            "m_correccion": _normalizar_score_01(parsed_metricas.get("correccion", 0)),
            "exp_correccion": safe_str(parsed_metricas.get("exp_correccion", "")),
            "score_total": m_cumplimiento,
            "resultado": clasificar_cumplimiento_metricas(m_cumplimiento),
            "justificacion": safe_str(parsed_metricas.get("justificacion", "")),
            "raw_json": json.dumps(parsed_metricas, ensure_ascii=False, indent=2),
            "latencia_eval_s": latency_clas_s,
        }

    except Exception as e:
        metricas_eval = build_error_juez_result_metricas(
            motivo=f"Error analizando salida del juez metrica: {type(e).__name__}: {e}",
            raw_json=safe_str(locals().get("content_clas", "")),
            latency_s=locals().get("latency_clas_s", 0.0),
        )

    eval_juez.update(
        {
            "resultado_metricas": metricas_eval.get("resultado", "FAIL"),
            "justificacion_metricas": metricas_eval.get("justificacion", ""),
            "score_total_metricas": metricas_eval.get("score_total", 0.0),
            "m_coherencia": metricas_eval.get("m_coherencia", 0.0),
            "exp_coherencia": metricas_eval.get("exp_coherencia", ""),
            "m_fluidez": metricas_eval.get("m_fluidez", 0.0),
            "exp_fluidez": metricas_eval.get("exp_fluidez", ""),
            "m_cumplimiento": metricas_eval.get("m_cumplimiento", 0.0),
            "exp_cumplimiento": metricas_eval.get("exp_cumplimiento", ""),
            "m_integridad": metricas_eval.get("m_integridad", 0.0),
            "exp_integridad": metricas_eval.get("exp_integridad", ""),
            "m_claridad": metricas_eval.get("m_claridad", 0.0),
            "exp_claridad": metricas_eval.get("exp_claridad", ""),
            "m_correccion": metricas_eval.get("m_correccion", 0.0),
            "exp_correccion": metricas_eval.get("exp_correccion", ""),
            "raw_json_metricas": metricas_eval.get("raw_json", "{}"),
            "latencia_eval_s_metricas": metricas_eval.get("latencia_eval_s", 0.0),
        }
    )

    return eval_juez


# ======================================================================================================================
# FIN DEL JUEZ
# ======================================================================================================================


# ======================================================================================================================
# METODO PARA CONECTARSE CON EL AGENTE DE PHOENIX
# ======================================================================================================================


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

    if response.status_code in CUSTOMER_PROC_RETRYABLE_STATUS:
        raise requests.HTTPError(
            f"Status transitorio {response.status_code} al insertar en DH_CUSTOMER_PROC",
            response=response,
        )

    response.raise_for_status()
    return response


def add_new_cic_to_customer_proc(request_cliente_json):
    print("INSERTANDO NUEVOS REGISTROS EN DH_CUSTOMER_PROC")
    headers_create = {"Content-Type": "application/json"}
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

    def _insert_with_retry():
        last_error = None
        for attempt in range(1, CUSTOMER_PROC_MAX_RETRIES + 1):
            try:
                response = _post_customer_proc(correct_payload, headers_create)
                print(
                    f"[DH_CUSTOMER_PROC] cic={cic} status={response.status_code} "
                    f"intento={attempt}/{CUSTOMER_PROC_MAX_RETRIES}"
                )
                print("Response body:", response.text)

                if CUSTOMER_PROC_SETTLE_DELAY_S > 0:
                    time.sleep(CUSTOMER_PROC_SETTLE_DELAY_S)
                return

            except requests.RequestException as exc:
                last_error = exc
                status_code = getattr(getattr(exc, "response", None), "status_code", None)
                response_body = getattr(getattr(exc, "response", None), "text", "")

                if attempt >= CUSTOMER_PROC_MAX_RETRIES:
                    break

                wait_s = round(CUSTOMER_PROC_RETRY_BACKOFF_S * attempt, 2)
                print(
                    f"[DH_CUSTOMER_PROC] cic={cic} fallo intento={attempt}/"
                    f"{CUSTOMER_PROC_MAX_RETRIES} status={status_code} "
                    f"esperando={wait_s}s para reintentar. Detalle={response_body}"
                )
                time.sleep(wait_s)

        raise RuntimeError(
            f"No se pudo insertar el cic={cic} en DH_CUSTOMER_PROC "
            f"tras {CUSTOMER_PROC_MAX_RETRIES} intentos. "
            f"Ultimo error: {type(last_error).__name__}: {last_error}"
        ) from last_error

    if SERIALIZE_CUSTOMER_PROC_WRITES:
        with _customer_proc_lock:
            _insert_with_retry()
    else:
        _insert_with_retry()


# ======================================================================================================================
# OTROS METODOS (FUNCIÓN PARA GENERAR EL PAYLOAD DEL REQ)
# ======================================================================================================================



def generar_payload(user_row):
    fake = Faker("es_ES")  # Español de España

    # Mapas para clasificación y segmento
    mapa_classification = {"I": "Intencionado", "AR": "Alto Riesgo", "R": "Reacio"}
    mapa_segments = {
        "PY_1": "PYME 01 -30",
        "PY_2": "PYME 31 - 120",
        "PY_3": "PYME 120+",
        "PE_1": "PERSONA 1-30",
        "PE_2": "PERSONA 31 - 60",
        "PE_3": "PERSONA 61 - 120",
        "PE_4": "PERSONA 120+",
    }

    # CIC
    cic_csv = safe_str(user_row.get("cic"))
    cic = cic_csv if cic_csv else f"{fake.random_number(digits=8, fix_len=True):08d}"

    # Helper para datos comerciales ficticios
    nombres_comerciales = [
        "Importaciones CUSCO",
        "Distribuidora Ucayali",
        "Restaurante Normita's",
        "Abarrotes Don Pepe",
        "Salon de Belleza Glam",
        "Agropecuaria El Puente",
        "Zapateria El Zapaton",
        "Maderera Torres EIRL",
        "Almacenes El Ucayalino" "RyR Importaciones",
    ]

    # Nombres y nombres comerciales
    tipo_seg_csv = safe_str(user_row.get("tipo_seg"))
    segmento_persona = tipo_seg_csv in ("PE_1", "PE_2", "PE_3", "PE_4")
    segmento_pyme = tipo_seg_csv in ("PY_1", "PY_2", "PY_3") or not tipo_seg_csv

    nombre = safe_str(user_row.get("nombre"))
    apellidos = safe_str(user_row.get("apellidos"))

    if segmento_persona:
        # Solo nombre de persona
        if nombre and apellidos:
            user_name = f"{nombre.strip()} {apellidos.strip()}".strip()
        elif not nombre and not apellidos:
            user_name = fake.name()
        else:
            user_name = nombre or apellidos or fake.name()
    elif segmento_pyme:
        # PYME: Comercial o persona completa (50/50 si ambos vacíos)
        if nombre and apellidos:
            user_name = f"{nombre.strip()} {apellidos.strip()}".strip()
        elif not nombre and not apellidos:
            # Puede ser comercial o persona
            user_name = (
                fake.name()
                if fake.pybool()
                else fake.random_element(nombres_comerciales)
            )
        else:
            user_name = (
                    nombre
                    or apellidos
                    or (
                        fake.name()
                        if fake.pybool()
                        else fake.random_element(nombres_comerciales)
                    )
            )
    else:
        # Otros casos (por si más adelante se agregan otros segmentos)
        if nombre and apellidos:
            user_name = f"{nombre.strip()} {apellidos.strip()}".strip()
        elif not nombre and not apellidos:
            user_name = (
                fake.name()
                if fake.pybool()
                else fake.random_element(nombres_comerciales)
            )
        else:
            user_name = (
                    nombre
                    or apellidos
                    or (
                        fake.name()
                        if fake.pybool()
                        else fake.random_element(nombres_comerciales)
                    )
            )

    # DNI
    dni_csv = safe_str(user_row.get("dni"))
    dni = dni_csv if dni_csv else f"{fake.random_number(digits=8, fix_len=True):08d}"

    # Teléfono
    phone_csv = safe_str(user_row.get("cel"))
    phone = phone_csv if phone_csv else fake.msisdn()[:9]

    # Segmentos
    tipo_seg_csv = safe_str(user_row.get("tipo_seg"))
    segments = (
        mapa_segments.get(tipo_seg_csv, "PERSONA 1 - 31")
        if tipo_seg_csv
        else fake.random_element(list(mapa_segments.values()))
    )

    # Clasificación
    tipo_cliente_csv = safe_str(user_row.get("tipo_cliente"))
    classification = (
        mapa_classification.get(tipo_cliente_csv, "Intencionado")
        if tipo_cliente_csv
        else fake.random_element(list(mapa_classification.values()))
    )

    # profile_quadrant: A/B/C/D (si viniera en CSV, lo respetas; si no, lo generas)
    pq_csv = safe_str(user_row.get("profile_quadrant")).strip().upper()
    profile_quadrant = (
        pq_csv
        if pq_csv in ("A", "B", "C", "D")
        else fake.random_element(["A", "B", "C", "D"])
    )

    # cod_customer_priority: fijo P5 (si quieres permitir override por CSV, lo puedes hacer)
    cod_customer_priority = "P5"

    ct_csv = safe_str(user_row.get("customer_type")).strip().upper()

    customer_type_validos = ("PERSONAS", "PYME NATURAL", "PYME JURIDICO")

    if ct_csv in customer_type_validos:
        customer_type = ct_csv
    else:
        tipo_seg_norm = safe_str(user_row.get("tipo_seg")).strip().upper()
        if tipo_seg_norm in ("PE_1", "PE_2", "PE_3", "PE_4"):
            customer_type = "PERSONAS"
        elif tipo_seg_norm == "PY_1":
            customer_type = "PYME NATURAL"
        elif tipo_seg_norm == "PY_2":
            customer_type = "PYME JURIDICO"
        else:
            customer_type = "PERSONAS"

    # Deuda soles
    deuda_soles_csv = safe_str(user_row.get("deuda_soles")).strip()
    val_debt_amount_1 = (
        float(deuda_soles_csv)
        if deuda_soles_csv
        else round(fake.pyfloat(right_digits=2, min_value=500, max_value=15000), 2)
    )
    val_currency1 = "Soles"
    cuenta_soles_csv = safe_str(user_row.get("cuenta_soles")).strip()
    accnum1 = (
        cuenta_soles_csv
        if cuenta_soles_csv
        else fake.bothify(text="016################", letters="")
    )

    # Deuda dólares
    deuda_dolares_csv = safe_str(user_row.get("deuda_dolares")).strip()
    val_debt_amount_2 = (
        float(deuda_dolares_csv)
        if deuda_dolares_csv
        else 0.0
    )
    val_currency2 = "Dólares"
    cuenta_dolares_csv = safe_str(user_row.get("cuenta_dolares")).strip()
    if deuda_dolares_csv and cuenta_dolares_csv:
        accnum2 = cuenta_dolares_csv
    elif deuda_dolares_csv and not cuenta_dolares_csv:
        accnum2 = fake.bothify(text="015################", letters="")
    else:
        accnum2 = str("")

    # Días vencidos
    qty_overdue_csv = safe_str(user_row.get("qty_overdue_days"))
    qty_overdue_days = (
        qty_overdue_csv if qty_overdue_csv else str(fake.random_int(min=1, max=90))
    )

    # Producto
    tipo_deuda_csv = safe_str(user_row.get("tipo_deuda"))
    posibles_prod = [
        "Activo Fijo",
        "Adelanto Sueldo",
        "Capital de Trabajo",
        "Crédito Efectivo",
        "Crédito Yape",
        "Crédito Vehicular",
        "Crédito Yape",
        "Cuotéalo",
        "Garantía Hipotecaria",
        "Hipotecario",
        "Impulsa Perú",
        "Mivivienda",
        "Reactiva Perú",
        "Refinanciado",
        "Reprogramado",
    ]
    product = tipo_deuda_csv if tipo_deuda_csv else fake.random_element(posibles_prod)

    # last_pdp
    last_pdp_csv = safe_str(user_row.get("last_pdp"))
    last_pdp = last_pdp_csv if last_pdp_csv else fake.random_element(["SI", "NO"])

    # active_pkg
    active_pkg = safe_str(user_row.get("active_pkg")) or "NO"
    client_statement_raw = safe_str(user_row.get("client_statement_raw")) or ""

    # ENSAMBLA EL PAYLOAD:
    payload = {
        "user_id": cic,
        "customer_data": {
            "user_name": user_name,
            "dni": dni,
            "phone": phone,
            "cic": cic,
            "segments": segments,
            "classification": classification,
            "val_debt_amount_1": val_debt_amount_1,
            "val_currency1": val_currency1,
            "account_number_1": accnum1,
            "val_debt_amount_2": val_debt_amount_2,
            "val_currency2": val_currency2,
            "account_number_2": accnum2,
            "qty_overdue_days": qty_overdue_days,
            "product": product,
            "last_pdp": last_pdp,
            "active_pkg": active_pkg,
            "client_statement_raw": client_statement_raw,
            # NUEVOS CAMPOS EN customer_data
            "profile_quadrant": profile_quadrant,
            "cod_customer_priority": cod_customer_priority,
            "customer_type": customer_type,
        },
    }
    # IMPRIMIR EL PAYLOAD
    print(
        "Payload generado para la fila:",
        json.dumps(payload, indent=2, ensure_ascii=False),
    )
    return payload


def obtener_datos_prompt_desde_payload(request_cliente_json):
    customer_data = request_cliente_json.get("customer_data", {})
    return {
        "nombre_completo": safe_str(customer_data.get("user_name")).strip(),
        "deuda_soles": safe_str(customer_data.get("val_debt_amount_1")).strip(),
        "deuda_dolares": safe_str(customer_data.get("val_debt_amount_2")).strip(),
        "cic": safe_str(customer_data.get("cic")).strip(),
        "dni": safe_str(customer_data.get("dni")).strip(),
        "cel": safe_str(customer_data.get("phone")).strip(),
        "tipo_deuda": safe_str(customer_data.get("product")).strip(),
    }


def send_bot_message(url_msg, headers_msg, message):
    payload_msg = {"message": message}
    print("--- DEBUG SEND BOT MESSAGE ---")
    print("URL:", url_msg)
    print("HEADERS:", headers_msg)
    print("PAYLOAD:", payload_msg)
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


def _normalizar_texto_para_match(texto):
    normalizado = safe_str(texto).lower()
    replacements = str.maketrans(
        {
            "á": "a",
            "é": "e",
            "í": "i",
            "ó": "o",
            "ú": "u",
            "ü": "u",
        }
    )
    return normalizado.translate(replacements)


def _bot_necesita_espera_cosmos(bot_text):
    txt = _normalizar_texto_para_match(bot_text)
    tiene_pdp = any(
        token in txt for token in ("pdp", "promesa de pago", "promesa")
    )
    pide_conformidad = any(
        token in txt
        for token in (
            "conformidad",
            "confirmas",
            "confirmar",
            "confirma",
            "de acuerdo",
            "esta de acuerdo",
            "aceptas",
            "autorizas",
            "validas",
        )
    )
    confirma_registro = any(
        token in txt
        for token in (
            "registro",
            "registrado",
            "registrada",
            "registrar",
            "se registro",
            "quedo registrada",
            "quedo registrado",
        )
    )
    return (tiene_pdp and pide_conformidad) or (tiene_pdp and confirma_registro)


def esperar_ventana_procesamiento(bot_text, id_test):
    if BASE_TURN_DELAY_S > 0:
        print(f"[ESPERA_BASE] id_test={id_test} delay={BASE_TURN_DELAY_S}s")
        time.sleep(BASE_TURN_DELAY_S)

    if PDP_CONFORMIDAD_DELAY_S > 0 and _bot_necesita_espera_cosmos(bot_text):
        print(
            f"[ESPERA_PDP] id_test={id_test} "
            f"delay={PDP_CONFORMIDAD_DELAY_S}s por mensaje de conformidad PDP"
        )
        time.sleep(PDP_CONFORMIDAD_DELAY_S)


def esperar_antes_de_enviar_cliente(id_test, origen=""):
    if CLIENT_MESSAGE_DELAY_S <= 0:
        return

    origen_txt = f" origen={origen}" if origen else ""
    print(
        f"[ESPERA_CLIENTE]{origen_txt} "
        f"id_test={id_test} delay={CLIENT_MESSAGE_DELAY_S}s"
    )
    time.sleep(CLIENT_MESSAGE_DELAY_S)


def construir_row_resultado(
        orden_csv,
        user,
        chat_id,
        request_cliente_json,
        tipo_cliente,
        caso_de_prueba,
        mensaje_inicio,
        secuencia_mensaje,
        cic,
        dni,
        cel,
        nombre_completo,
        deuda_soles,
        deuda_dolares,
        tipo_deuda,
        status,
        bot_turns,
        total_bot_latency_s,
        total_sim_latency_s,
        last_bot,
        reglas_cliente,
        reglas_juez,
        conversa,
        eval_juez,
        perfil_juez,
        scenario_exec_time,
):
    row = {
        "_orden_csv": orden_csv,
        "_scenario_seconds": scenario_exec_time.total_seconds(),
        "id_test": safe_str(user.get("id_test")),
        "chat_id": safe_str(chat_id),
        "caso_de_prueba": caso_de_prueba,
        "tipo_cliente": tipo_cliente,
        "perfil_juez": perfil_juez,
        "cic": cic,
        "dni": dni,
        "cel": cel,
        "nombre_completo": nombre_completo,
        "deuda_soles": deuda_soles,
        "deuda_dolares": deuda_dolares,
        "tipo_deuda": tipo_deuda,
        "status": status,
        "bot_turns": bot_turns,
        "bot_latency_s_total": round(total_bot_latency_s, 2),
        "sim_latency_s_total": round(total_sim_latency_s, 2),
        "mensaje_inicio": mensaje_inicio,
        "answer_last_bot": last_bot,
        "reglas_cliente": reglas_cliente,
        "reglas_juez": reglas_juez,
        "conversa": json.dumps(conversa, ensure_ascii=False),
        "status_prueba": eval_juez["resultado"],
        "comentario_status_prueba": eval_juez["justificacion"],
        "score_total": eval_juez["score_total"],
        "total_cumple": eval_juez["total_cumple"],
        "total_no_cumple": eval_juez["total_no_cumple"],
        "total_no_aplica": eval_juez["total_no_aplica"],
        "total_aplicables": eval_juez["total_aplicables"],
        "json_juez": eval_juez["raw_json"],
        "latencia_eval_s": eval_juez["latencia_eval_s"],
        "status_prueba_metricas": eval_juez.get("resultado_metricas", "FAIL"),
        "comentario_status_prueba_metricas": eval_juez.get(
            "justificacion_metricas", ""
        ),
        "score_total_metricas": eval_juez.get("score_total_metricas", 0.0),
        "m_coherencia": eval_juez.get("m_coherencia", 0.0),
        "exp_coherencia": eval_juez.get("exp_coherencia", ""),
        "m_fluidez": eval_juez.get("m_fluidez", 0.0),
        "exp_fluidez": eval_juez.get("exp_fluidez", ""),
        "m_cumplimiento": eval_juez.get("m_cumplimiento", 0.0),
        "exp_cumplimiento": eval_juez.get("exp_cumplimiento", ""),
        "m_integridad": eval_juez.get("m_integridad", 0.0),
        "exp_integridad": eval_juez.get("exp_integridad", ""),
        "m_claridad": eval_juez.get("m_claridad", 0.0),
        "exp_claridad": eval_juez.get("exp_claridad", ""),
        "m_correccion": eval_juez.get("m_correccion", 0.0),
        "exp_correccion": eval_juez.get("exp_correccion", ""),
        "json_juez_metricas": eval_juez.get("raw_json_metricas", "{}"),
        "latencia_eval_s_metricas": eval_juez.get("latencia_eval_s_metricas", 0.0),
        "payload": json.dumps(request_cliente_json, ensure_ascii=False, indent=2),
        "tiempo_ejecucion": format_td_hms(scenario_exec_time),
        "secuencia_mensaje": "\n".join(secuencia_mensaje),
    }

    for key, _ in FUNCIONALIDADES_JUEZ:
        row[f"{key}_score"] = eval_juez.get(f"{key}_score", 0)
        row[f"{key}_justification"] = eval_juez.get(f"{key}_justification", "")

    return row


def ejecutar_escenario_phoenix(orden_csv, user):
    scenario_start = datetime.now()
    id_test = safe_str(user.get("id_test"))
    tipo_cliente = safe_str(user.get("tipo_cliente"))
    caso_de_prueba = safe_str(user.get("caso_de_prueba"))
    mensaje_inicio = safe_str(user.get("mensaje_inicio"))
    secuencia_mensaje = parsear_secuencia_mensajes(user.get("secuencia_mensaje"))
    cic = safe_str(user.get("cic"))
    dni = safe_str(user.get("dni"))
    cel = safe_str(user.get("Cel"))
    nombre = safe_str(user.get("nombre"))
    apellidos = safe_str(user.get("apellidos"))
    deuda_soles = safe_str(user.get("deuda_soles"))
    deuda_dolares = safe_str(user.get("deuda_dolares"))
    tipo_deuda = safe_str(user.get("tipo_deuda"))
    identidad_del_cliente = safe_str(user.get("identidad_del_cliente"))
    voluntad_de_pago = safe_str(user.get("voluntad_de_pago"))
    capacidad_pago = safe_str(user.get("capacidad_pago"))
    estilo_respuesta = safe_str(user.get("estilo_respuesta"))
    actitud_comportamiento = safe_str(user.get("actitud_comportamiento"))
    barreras_whatssapp = safe_str(user.get("barreras_whatssapp"))
    frases_comunes = safe_str(user.get("frases_comunes"))
    reglas_muy_importante = safe_str(user.get("reglas_muy_importante"))
    reglas_cliente = safe_str(user.get("reglas_negocio_cliente"))
    reglas_juez = safe_str(user.get("reglas_negocio_juez"))
    nombre_completo = (nombre + " " + apellidos).strip()

    request_cliente_json = {}
    chat_id = ""
    conversa = []
    status = "OK"
    bot_turns = 0
    last_bot = ""
    total_bot_latency_s = 0.0
    total_sim_latency_s = 0.0
    full_conversation = ""
    perfil_juez = ""
    eval_juez = build_error_juez_result("No se ejecutó el juez por funcionalidades.")
    metricas_eval = build_error_juez_result_metricas(
        "No se ejecutó el juez metrica."
    )
    eval_juez.update(
        {
            "resultado_metricas": metricas_eval.get("resultado", "FAIL"),
            "justificacion_metricas": metricas_eval.get("justificacion", ""),
            "score_total_metricas": metricas_eval.get("score_total", 0.0),
            "m_coherencia": metricas_eval.get("m_coherencia", 0.0),
            "exp_coherencia": metricas_eval.get("exp_coherencia", ""),
            "m_fluidez": metricas_eval.get("m_fluidez", 0.0),
            "exp_fluidez": metricas_eval.get("exp_fluidez", ""),
            "m_cumplimiento": metricas_eval.get("m_cumplimiento", 0.0),
            "exp_cumplimiento": metricas_eval.get("exp_cumplimiento", ""),
            "m_integridad": metricas_eval.get("m_integridad", 0.0),
            "exp_integridad": metricas_eval.get("exp_integridad", ""),
            "m_claridad": metricas_eval.get("m_claridad", 0.0),
            "exp_claridad": metricas_eval.get("exp_claridad", ""),
            "m_correccion": metricas_eval.get("m_correccion", 0.0),
            "exp_correccion": metricas_eval.get("exp_correccion", ""),
            "raw_json_metricas": metricas_eval.get("raw_json", "{}"),
            "latencia_eval_s_metricas": metricas_eval.get("latencia_eval_s", 0.0),
        }
    )

    try:
        request_cliente_json = generar_payload(user)
        datos_prompt = obtener_datos_prompt_desde_payload(request_cliente_json)
        nombre_completo = datos_prompt.get("nombre_completo") or nombre_completo
        deuda_soles = datos_prompt.get("deuda_soles") or deuda_soles
        deuda_dolares = datos_prompt.get("deuda_dolares") or deuda_dolares
        cic = datos_prompt.get("cic") or cic
        dni = datos_prompt.get("dni") or dni
        cel = datos_prompt.get("cel") or cel
        tipo_deuda = datos_prompt.get("tipo_deuda") or tipo_deuda
        perfil_juez = safe_str(
            request_cliente_json.get("customer_data", {}).get("classification", "")
        )
        prompt_cliente = get_prompt_por_tipo(
            tipo_cliente,
            nombre_completo,
            deuda_soles,
            deuda_dolares,
            identidad_del_cliente,
            voluntad_de_pago,
            capacidad_pago,
            estilo_respuesta,
            actitud_comportamiento,
            barreras_whatssapp,
            frases_comunes,
            reglas_muy_importante,
        )

        print(f"[INICIO] Escenario {orden_csv + 1}: {id_test}")
        add_new_cic_to_customer_proc(request_cliente_json)
        chat_id, url_msg, headers_msg = create_chat_and_headers(request_cliente_json)

        conversa.append(("usuario", mensaje_inicio))
        esperar_antes_de_enviar_cliente(id_test, "inicio")
        bot_text, bot_lat, exit_status, data = send_bot_message(
            url_msg, headers_msg, mensaje_inicio
        )
        total_bot_latency_s += bot_lat
        bot_turns += 1
        last_bot = bot_text
        conversa.append(("bot", bot_text))
        esperar_ventana_procesamiento(bot_text, id_test)

        # ==========================================================
        # SECUENCIA DE MENSAJES DEFINIDOS EN CSV
        # ==========================================================
        for mensaje_secuencia in secuencia_mensaje:
            if exit_status == 1:
                status = "BOT indicó fin de conversación (exit_status=1) durante secuencia definida"
                print(f"[EXIT_STATUS=1] Último mensaje del BOT: {bot_text}")
                ultimate_response = data
                break
            mensaje_secuencia = safe_str(mensaje_secuencia).strip()
            if not mensaje_secuencia:
                continue
            print(f"[{id_test}] MENSAJE SECUENCIA => {repr(mensaje_secuencia)}")
            conversa.append(("usuario", mensaje_secuencia))
            esperar_antes_de_enviar_cliente(id_test, "secuencia")
            bot_text, bot_lat, exit_status, data = send_bot_message(
                url_msg, headers_msg, mensaje_secuencia
            )
            total_bot_latency_s += bot_lat
            bot_turns += 1
            last_bot = bot_text
            conversa.append(("bot", bot_text))
            esperar_ventana_procesamiento(bot_text, id_test)
        # ==========================================================
        # SI LA SECUENCIA TERMINÓ Y EL BOT NO CERRÓ, ENTRA USER-SIMULATOR
        # ==========================================================
        turn_count = 0
        while True:
            if exit_status == 1:
                status = "BOT indicó fin de conversación (exit_status=1)"
                print(f"[EXIT_STATUS=1] Último mensaje del BOT: {bot_text}")
                ultimate_response = data
                break
            if turn_count >= MAX_TURNS_SAFE:
                status = "CORTADO: Exceso de turnos (posible bucle infinito)"
                break
            t0 = datetime.now()
            sim_text = llamada_user_simulator(prompt_cliente, conversa)
            sim_lat = round((datetime.now() - t0).total_seconds(), 2)
            total_sim_latency_s += sim_lat
            turn_count += 1
            print(
                f"[{id_test} | {nombre_completo} | {tipo_cliente}] CLIENTE => {repr(sim_text)}"
            )
            if not sim_text:
                status = "ERROR: USER-SIMULATOR devolvió vacío"
                break
            if sim_text.strip().lower() in ["fin", "adios", "adiós"]:
                status = "OK (simulador terminó)"
                break
            conversa.append(("usuario", sim_text))
            esperar_antes_de_enviar_cliente(id_test, "simulador")
            bot_text, bot_lat, exit_status, data = send_bot_message(
                url_msg, headers_msg, sim_text
            )
            total_bot_latency_s += bot_lat
            bot_turns += 1
            last_bot = bot_text
            conversa.append(("bot", bot_text))
            esperar_ventana_procesamiento(bot_text, id_test)

    except Exception as e:
        status = f"ERROR {type(e).__name__}: {e}"
    finally:
        scenario_end = datetime.now()
        scenario_exec_time = scenario_end - scenario_start
        full_conversation = build_full_conversation(conversa)

    try:
        perfil_juez = safe_str(
            request_cliente_json.get("customer_data", {}).get("classification", "")
        )

        # if RUN_LLM_JUDGE:
        eval_juez = llm_judge_metricas(
            question=full_conversation,
            perfil=perfil_juez,
            caso_de_prueba=caso_de_prueba,
            reglas_juez=reglas_juez,
        )

    except Exception as e:
        eval_juez = build_error_juez_result(
            motivo=f"Excepción ejecutando juez de funcionalidades: {type(e).__name__}: {e}",
            raw_json="{}",
            latency_s=0.0,
        )
        metricas_eval = build_error_juez_result_metricas(
            motivo=f"Excepción ejecutando juez métricas: {type(e).__name__}: {e}",
            raw_json="{}",
            latency_s=0.0,
        )
        eval_juez.update(
            {
                "resultado_metricas": metricas_eval.get("resultado", "FAIL"),
                "justificacion_metricas": metricas_eval.get("justificacion", ""),
                "score_total_metricas": metricas_eval.get("score_total", 0.0),
                "m_coherencia": metricas_eval.get("m_coherencia", 0.0),
                "exp_coherencia": metricas_eval.get("exp_coherencia", ""),
                "m_fluidez": metricas_eval.get("m_fluidez", 0.0),
                "exp_fluidez": metricas_eval.get("exp_fluidez", ""),
                "m_cumplimiento": metricas_eval.get("m_cumplimiento", 0.0),
                "exp_cumplimiento": metricas_eval.get("exp_cumplimiento", ""),
                "m_integridad": metricas_eval.get("m_integridad", 0.0),
                "exp_integridad": metricas_eval.get("exp_integridad", ""),
                "m_claridad": metricas_eval.get("m_claridad", 0.0),
                "exp_claridad": metricas_eval.get("exp_claridad", ""),
                "m_correccion": metricas_eval.get("m_correccion", 0.0),
                "exp_correccion": metricas_eval.get("exp_correccion", ""),
                "raw_json_metricas": metricas_eval.get("raw_json", "{}"),
                "latencia_eval_s_metricas": metricas_eval.get("latencia_eval_s", 0.0),
            }
        )

    row = construir_row_resultado(
        orden_csv,
        user,
        chat_id,
        request_cliente_json,
        tipo_cliente,
        caso_de_prueba,
        mensaje_inicio,
        secuencia_mensaje,
        cic,
        dni,
        cel,
        nombre_completo,
        deuda_soles,
        deuda_dolares,
        tipo_deuda,
        status,
        bot_turns,
        total_bot_latency_s,
        total_sim_latency_s,
        last_bot,
        reglas_cliente,
        reglas_juez,
        conversa,
        eval_juez,
        perfil_juez,
        scenario_exec_time,
    )

    return row


def ejecutar_escenarios_en_paralelo(df_escenarios):
    total_escenarios = len(df_escenarios)
    if total_escenarios == 0:
        return [], timedelta(0)

    max_workers = obtener_max_workers(total_escenarios)
    print(
        f"[INFO] Ejecutando {total_escenarios} escenarios "
        f"en paralelo con {max_workers} worker(s)."
    )

    rows_resultado = []
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futuros = {}
        for orden_csv, (_, user) in enumerate(df_escenarios.iterrows()):
            future = executor.submit(ejecutar_escenario_phoenix, orden_csv, user.copy())
            futuros[future] = orden_csv

        completados = 0
        pendientes = set(futuros.keys())
        t_inicio = time.monotonic()

        try:
            while pendientes:
                if PARALLEL_GLOBAL_TIMEOUT_S > 0:
                    elapsed_total = time.monotonic() - t_inicio
                    if elapsed_total >= PARALLEL_GLOBAL_TIMEOUT_S:
                        for f in pendientes:
                            f.cancel()
                        pendientes_orden = sorted(futuros[f] + 1 for f in pendientes)
                        raise TimeoutError(
                            "Timeout global en paralelo "
                            f"({PARALLEL_GLOBAL_TIMEOUT_S}s). "
                            f"Pendientes: {pendientes_orden}"
                        )

                done, pendientes = wait(
                    pendientes,
                    timeout=PARALLEL_PROGRESS_LOG_EVERY_S,
                    return_when=FIRST_COMPLETED,
                )

                if not done:
                    print(
                        "[PROGRESO] Esperando escenarios pendientes: "
                        f"{len(pendientes)}/{total_escenarios}"
                    )
                    continue

                for future in done:
                    completados += 1
                    rows_resultado.append(future.result())
                    print(
                        f"[PROGRESO] {completados}/{total_escenarios} escenarios completados"
                    )
        except KeyboardInterrupt:
            for f in pendientes:
                f.cancel()
            pendientes_orden = sorted(futuros[f] + 1 for f in pendientes)
            print(
                "[INTERRUPT] Ejecucion interrumpida por usuario. "
                f"Escenarios completados: {completados}/{total_escenarios}. "
                f"Pendientes cancelados: {pendientes_orden}"
            )

    rows_resultado.sort(key=lambda row: row.get("_orden_csv", 0))
    total_seconds = sum(row.pop("_scenario_seconds", 0.0) for row in rows_resultado)

    for row in rows_resultado:
        row.pop("_orden_csv", None)

    return rows_resultado, timedelta(seconds=total_seconds)


# ======================================================================================================================
# CARGA CSV
# ======================================================================================================================
df_users = pd.read_csv(
    CSV_PATH,
    sep=CSV_SEP,
    encoding="utf-8",
    engine="python",
    quoting=1,
    # dtype={"cic": str}
)

df_users = df_users[df_users["ejecutar_prueba"] == 1]

df_users_ejecutar = df_users.copy()

global_start = datetime.now()
rows, total_exec_time = ejecutar_escenarios_en_paralelo(df_users_ejecutar)
global_end = datetime.now()
wall_exec_time = global_end - global_start
total_exec_time_formatted = format_td_hms(total_exec_time)
wall_exec_time_formatted = format_td_hms(wall_exec_time)
df = pd.DataFrame(rows)
print(df.head())

# Contadores por bloque de evaluacion (funcionalidades vs metricas)
total_cases = len(df)

status_func = df["status_prueba"].astype(str).str.upper() if "status_prueba" in df.columns else pd.Series([], dtype=str)
status_metricas = (
    df["status_prueba_metricas"].astype(str).str.upper()
    if "status_prueba_metricas" in df.columns
    else pd.Series([], dtype=str)
)

total_pass_func = int(status_func.eq("PASS").sum())
total_warning_func = int(status_func.eq("WARNING").sum())
total_fail_func = int(status_func.eq("FAIL").sum())

total_pass_metricas = int(status_metricas.eq("PASS").sum())
total_warning_metricas = int(status_metricas.eq("WARNING").sum())
total_fail_metricas = int(status_metricas.eq("FAIL").sum())

pass_percent_func = round((total_pass_func / total_cases) * 100) if total_cases else 0
warning_percent_func = round((total_warning_func / total_cases) * 100) if total_cases else 0
fail_percent_func = round((total_fail_func / total_cases) * 100) if total_cases else 0

pass_percent_metricas = round((total_pass_metricas / total_cases) * 100) if total_cases else 0
warning_percent_metricas = round((total_warning_metricas / total_cases) * 100) if total_cases else 0
fail_percent_metricas = round((total_fail_metricas / total_cases) * 100) if total_cases else 0


def calcular_porcentaje(valor, total):
    if not total:
        return 0
    return round((valor / total) * 100, 2)


def calcular_detalle_cumplimiento(df_resultados):
    total_escenarios = len(df_resultados)
    filas = []

    for key, label in FUNCIONALIDADES_VISIBLES_REPORTE:
        score_col = f"{key}_score"
        if score_col in df_resultados.columns:
            scores = df_resultados[score_col].apply(normalizar_score_funcionalidad)
        else:
            scores = pd.Series([], dtype=int)

        cumple = int(scores.eq(1).sum())
        no_cumple = int(scores.eq(0).sum())
        no_aplica = int(scores.eq(-1).sum())
        aplica = cumple + no_cumple
        escenarios = aplica + no_aplica

        # Nota: en la seccion "Aplica", los porcentajes deben calcularse
        # sobre los casos aplicables de esa funcionalidad.
        denom_aplica = aplica if aplica > 0 else 0
        # Para "Aplica/No Aplica" global de la funcionalidad, usar el total
        # de escenarios efectivamente clasificados en esa funcionalidad.
        denom_total_func = escenarios if escenarios > 0 else total_escenarios

        filas.append(
            {
                "key": key,
                "funcionalidad": label,
                "cumple": cumple,
                "cumple_pct": calcular_porcentaje(cumple, denom_aplica),
                "no_cumple": no_cumple,
                "no_cumple_pct": calcular_porcentaje(no_cumple, denom_aplica),
                "no_aplica": no_aplica,
                "no_aplica_pct": calcular_porcentaje(no_aplica, denom_total_func),
                "aplica": aplica,
                "aplica_pct": calcular_porcentaje(aplica, denom_total_func),
                "escenarios": escenarios,
                "total_escenarios": total_escenarios,
            }
        )

    return {
        "total_escenarios": total_escenarios,
        "filas": filas,
    }


def calcular_escenarios_por_funcionalidad(df_resultados):
    estados = [
        (1, "cumple", "Cumple"),
        (0, "no_cumple", "No Cumple"),
        (-1, "no_aplica", "No Aplica"),
    ]
    detalle = {}

    for key, label in FUNCIONALIDADES_VISIBLES_REPORTE:
        detalle[key] = {
            "label": label,
            "estados": {
                estado_key: {
                    "label": estado_label,
                    "escenarios": [],
                }
                for _, estado_key, estado_label in estados
            },
        }
        detalle[key]["estados"]["aplica"] = {
            "label": "Aplica",
            "escenarios": [],
        }

        score_col = f"{key}_score"
        justification_col = f"{key}_justification"

        for _, row in df_resultados.iterrows():
            score = normalizar_score_funcionalidad(row.get(score_col, 0))
            estado_key = next((item[1] for item in estados if item[0] == score), "no_cumple")
            escenario_detalle = {
                "id_test": safe_str(row.get("id_test", "")),
                "escenario": safe_str(row.get("caso_de_prueba", "")),
                "justificacion": safe_str(row.get(justification_col, "")),
            }
            detalle[key]["estados"][estado_key]["escenarios"].append(escenario_detalle)
            if score != -1:
                detalle[key]["estados"]["aplica"]["escenarios"].append(escenario_detalle)

    return detalle


detalle_cumplimiento = calcular_detalle_cumplimiento(df)
escenarios_por_funcionalidad = calcular_escenarios_por_funcionalidad(df)


# ======================================================================================================================
# REPORTE HTML
# ======================================================================================================================
def escape_cell(val):
    if isinstance(val, (dict, list)):
        return html.escape(json.dumps(val, ensure_ascii=False, indent=2))
    return html.escape(str(val) if val is not None else "")


def checklist_juez_table(judge_json_str):
    try:
        data = json.loads(judge_json_str)
    except Exception:
        return "<i>Sin evaluación</i>"
    criterios = [
        ("empatia", "Empatía"),
        ("escucha_activa", "Escucha activa"),
        ("propuestas_solucion", "Propuestas de solución"),
        ("flexibilidad_operativa", "Flexibilidad operativa"),
        ("claridad_transparencia", "Claridad y transparencia"),
        ("proactividad_cierre", "Proactividad y cierre"),
        ("respeto_no_presion", "Respeto y no presión"),
        ("ortografia_gramatica", "Ortografía y gramática"),
        ("coherencia_consistencia", "Coherencia y consistencia"),
        ("reglas_negocio", "Reglas de negocio"),
    ]
    obs = data.get("observaciones", {})
    rows_html = []
    for key, label in criterios:
        puntaje = data.get(key, "")
        observ = obs.get(key, "") if obs else ""
        rows_html.append(
            f"<tr><td>{label}</td><td align='center'>{puntaje}</td><td>{html.escape(str(observ))}</td></tr>"
        )
    total = data.get("total", "")
    clasif = data.get("clasificacion", "")
    status = (
        "<span style='font-weight:bold; color:red'>ERROR</span>"
        if not data
        else (clasif or "")
    )
    rows_html.append(
        f"<tr style='font-weight:bold'><td>TOTAL</td><td align='center'>{total}</td><td>{status}</td></tr>"
    )
    return f"""
<div style="min-width:350px;max-width:500px;">
<b>Checklist de Evaluación</b>
<table style="border-collapse:collapse;margin-top:7px;width:100%;font-size:13px;">
<thead>
<tr>
<th style="border:1px solid #e6e6e6;">CRITERIO</th>
<th style="border:1px solid #e6e6e6;">PUNTAJE</th>
<th style="border:1px solid #e6e6e6;">OBSERVACIÓN</th>
</tr>
</thead>
<tbody>
         {''.join(rows_html)}
</tbody>
</table>
</div>
   """.replace("\n", "")


def link_details_juez(judge_json_str):
    html_checklist = checklist_juez_table(judge_json_str)
    return f"""
<details class="result">
<summary>Ver Evaluación</summary>
<div class="box">{html_checklist}</div>
</details>
   """


def badge_status(status):
    status = (status or "").strip().upper()
    if status == "PASS":
        return "<span class='badge-pass'>PASS</span>"
    elif status == "FAIL":
        return "<span class='badge-fail'>FAIL</span>"
    return f"<span>{status}</span>"


def link_details_conversa(hist_json_str):
    try:
        hist_list = json.loads(hist_json_str)
        out = ""
        for quien, texto in hist_list:
            out += f"[{str(quien).upper()}] {texto}\n\n"
        # Aquí va el reemplazo, inmediatamente después de armar 'out':
        out = out.replace("[USUARIO]", "[CLIENTE]").replace("[BOT]", "[AG. PHOENIX]")
        safe = html.escape(out.strip())
    except Exception:
        safe = html.escape(hist_json_str or "")
    return f"""
<details class="result">
<summary>Visualizar</summary>
<div class="box"><pre>{safe}</pre></div>
</details>
   """


# ===================================================================================================
#                 === NUEVO BLOQUE PARA ARMAR EL BUFFER DE CONTENIDOS DE MODAL EN JS ===
# ===================================================================================================

columns = [
    "Cod. Test",
    "Escenario",
    "Cumplimiento",
    "Coherencia",
    "Fluidez",
    "Integridad",
    "Claridad",
    "Corrección",
    "Puntuación",
    "Tiempo Ejecución",
    "Resultado",
    "Acciones",
]

FUNCIONALIDADES_COLUMNAS_REPORTE = [
    "Persuasión total",
    "Persuasión parcial",
    "Motivos no pago",
    "Registro pdp",
    "Canales atención",
    "Registro nps",
    "Ofrecer asesor",
    "Registro cita",
    "Consecuencias no pago",
    "Preguntas frecuentes",
]

metricas_COLUMNAS_REPORTE = [
    "Cumplimiento",
    "Coherencia",
    "Fluidez",
    "Integridad",
    "Claridad",
    "Corrección",
]

def resumir_texto(texto, max_chars=70):
    texto = safe_str(texto).strip().replace("\n", " ")
    while "  " in texto:
        texto = texto.replace("  ", " ")
    if len(texto) <= max_chars:
        return texto
    return texto[:max_chars].rsplit(" ", 1)[0] + "..."


def visualizar_modal(idx, tipo, titulo, icono="chat"):
    titulo_safe = html.escape(titulo)
    icon_svg = ""
    if icono == "chat":
        icon_svg = """
<svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2">
<path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path>
</svg>
       """
    elif icono == "data":
        icon_svg = """
<svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2">
<path d="M4 6h16M4 12h16M4 18h16"></path>
</svg>
       """
    else:
        icon_svg = """
<svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2">
<path d="M12 20h9"></path>
<path d="M16.5 3.5a2.1 2.1 0 1 1 3 3L7 19l-4 1 1-4Z"></path>
</svg>
       """
    return f"""
<button type="button" class="icon-btn"
       data-content-idx="{idx}"
       data-content-tipo="{tipo}"
       data-title="{titulo_safe}"
       onclick="showUniqueModalFromButton(this); openGlobalModal();"
       title="{titulo_safe}">
       {icon_svg}
</button>
   """


def badge_metrica_metrica(score):
    score = _normalizar_score_01(score)
    if score >= 0.8:
        cls = "badge-metrica-pass"
    elif score >= 0.5:
        cls = "badge-metrica-warning"
    else:
        cls = "badge-metrica-fail"
    return f"<span class='badge-metrica {cls}'>{score:.2f}</span>"


def badge_funcionalidad(score):
    score = normalizar_score_funcionalidad(score)
    if score == 1:
        return "<span class='badge-cumple'>CUMPLE</span>"
    if score == 0:
        return "<span class='badge-no-cumple'>NO CUMPLE</span>"
    return "<span class='badge-no-aplica'>NO APLICA</span>"


html_tablerows = []
modal_contents = []

for i, (_, r) in enumerate(df.iterrows()):

    funcionalidades_metricas = []
    for key, label in FUNCIONALIDADES_VISIBLES_REPORTE:
        score_func = normalizar_score_funcionalidad(r.get(f"{key}_score", 0))
        if score_func == 1:
            estado_func = "CUMPLE"
        elif score_func == 0:
            estado_func = "NO CUMPLE"
        else:
            estado_func = "NO APLICA"

        funcionalidades_metricas.append(
            {
                "mode": "funcionalidad",
                "key": key,
                "label": label,
                "score": score_func,
                "estado": estado_func,
                "justification": safe_str(r.get(f"{key}_justification", "")),
            }
        )

    detalle_metricas = {
        "metricas_funcionalidades": funcionalidades_metricas,
        "metricas": [
            {
                "mode": "metricas",
                "key": "cumplimiento",
                "label": "Cumplimiento",
                "score": _normalizar_score_01(r.get("m_cumplimiento", 0.0)),
                "justification": safe_str(r.get("exp_cumplimiento", "")),
            },
            {
                "mode": "metricas",
                "key": "coherencia",
                "label": "Coherencia",
                "score": _normalizar_score_01(r.get("m_coherencia", 0.0)),
                "justification": safe_str(r.get("exp_coherencia", "")),
            },
            {
                "mode": "metricas",
                "key": "fluidez",
                "label": "Fluidez",
                "score": _normalizar_score_01(r.get("m_fluidez", 0.0)),
                "justification": safe_str(r.get("exp_fluidez", "")),
            },
            {
                "mode": "metricas",
                "key": "integridad",
                "label": "Integridad",
                "score": _normalizar_score_01(r.get("m_integridad", 0.0)),
                "justification": safe_str(r.get("exp_integridad", "")),
            },
            {
                "mode": "metricas",
                "key": "claridad",
                "label": "Claridad",
                "score": _normalizar_score_01(r.get("m_claridad", 0.0)),
                "justification": safe_str(r.get("exp_claridad", "")),
            },
            {
                "mode": "metricas",
                "key": "correccion",
                "label": "Corrección",
                "score": _normalizar_score_01(r.get("m_correccion", 0.0)),
                "justification": safe_str(r.get("exp_correccion", "")),
            },
        ],
        "resumen_funcionalidades": r.get("comentario_status_prueba", ""),
        "resumen_metricas": r.get("comentario_status_prueba_metricas", ""),
    }

    fila_modal = {
        "payload": str(r.get("payload", "")),
        "conversa": "",
        "detalle_metricas": detalle_metricas,
    }

    try:
        hist_list = json.loads(r.get("conversa", "[]"))
        out = ""

        for quien, texto in hist_list:
            out += f"[{str(quien).upper()}] {texto}\n\n"

        out = out.replace("[USUARIO]", "[CLIENTE]").replace("[BOT]", "[AG. PHOENIX]")
        fila_modal["conversa"] = out.strip()

    except Exception:
        fila_modal["conversa"] = r.get("conversa", "") or ""

    modal_contents.append(fila_modal)

    status_func = safe_str(r.get("status_prueba")).upper()

    score = float(r.get("score_total_metricas", 0))
    status = safe_str(r.get("status_prueba_metricas")).upper()

    badge_func = (
        "<span class='badge-pass'>PASS</span>"
        if status_func == "PASS"
        else (
            "<span class='badge-warning'>WARNING</span>"
            if status_func == "WARNING"
            else "<span class='badge-fail'>FAIL</span>"
        )
    )

    badge = (
        "<span class='badge-pass'>PASS</span>"
        if status == "PASS"
        else (
            "<span class='badge-warning'>WARNING</span>"
            if status == "WARNING"
            else "<span class='badge-fail'>FAIL</span>"
        )
    )

    score_class = (
        "score-pass"
        if status == "PASS"
        else ("score-warning" if status == "WARNING" else "score-fail")
    )
    score_pct = max(0, min(100, round(score * 100)))

    metric_cells_func = ""
    for key, label in FUNCIONALIDADES_VISIBLES_REPORTE:
        metric_cells_func += (
            f"<td class=\"col-func\" data-label=\"{html.escape(label)}\">"
            f"{badge_funcionalidad(r.get(f'{key}_score', 0))}</td>"
        )

    metric_cells_clas = ""
    metricas_tabla = [
        ("Cumplimiento", r.get("m_cumplimiento", 0.0)),
        ("Coherencia", r.get("m_coherencia", 0.0)),
        ("Fluidez", r.get("m_fluidez", 0.0)),
        ("Integridad", r.get("m_integridad", 0.0)),
        ("Claridad", r.get("m_claridad", 0.0)),
        ("Corrección", r.get("m_correccion", 0.0)),
    ]
    for label, value in metricas_tabla:
        metric_cells_clas += (
            f"<td class=\"col-clas\" data-label=\"{html.escape(label)}\">"
            f"{badge_metrica_metrica(value)}</td>"
        )

    row_html = f"""
<tr data-result-func="{status_func}" data-result-clas="{status}">
<td data-label="Cod. Test">{escape_cell(r.get("id_test"))}</td>
<td data-label="Escenario" class="td-ellipsis" title="{escape_cell(r.get('caso_de_prueba'))}">
    {html.escape(resumir_texto(r.get("caso_de_prueba"), 42))}
</td>



{metric_cells_func}



{metric_cells_clas}



<td class="col-clas" data-label="Puntuacion">
<div class="score-wrap">
<div class="{score_class}">{score:.2f}</div>
<div class="score-bar">
<div class="score-fill {'fill-pass' if status == 'PASS' else ('fill-warning' if status == 'WARNING' else 'fill-fail')}" style="width:{score_pct}%"></div>
</div>
</div>
</td>
<td data-label="Tiempo Ejecucion" class="td-exec-time">{escape_cell(r.get("tiempo_ejecucion"))}</td>
<td class="col-func" data-label="Resultado">{badge_func}</td>
<td class="col-clas" data-label="Resultado">{badge}</td>
<td data-label="Acciones">
<div class="action-group">
        {visualizar_modal(i, 'conversa', 'CONVERSACIÓN', 'chat')}
        {visualizar_modal(i, 'payload', 'DATA', 'data')}
        {visualizar_modal(i, 'detalle_metricas', 'DETALLE MÉTRICAS', 'metricas')}
</div>
</td>
</tr>
"""

    html_tablerows.append(row_html)

html_modal_contents = (
        "<script>\nwindow.__MODAL_CONTENTS__ = "
        + json.dumps(modal_contents, ensure_ascii=False)
    + ";\nwindow.__DETALLE_CUMPLIMIENTO__ = "
    + json.dumps(detalle_cumplimiento, ensure_ascii=False)
    + ";\nwindow.__ESCENARIOS_FUNCIONALIDAD__ = "
    + json.dumps(escenarios_por_funcionalidad, ensure_ascii=False)
        + ";\n</script>"
)

html_table = f"""
<div class="table-card">
<div class="table-card-header">
<div class="table-title">Resultados por Escenario</div>
<div class="table-header-actions">
<button type="button" class="summary-modal-btn"
    data-content-tipo="detalle_cumplimiento"
    data-title="DETALLE CUMPLIMIENTO"
    aria-label="Detalle Cumplimiento"
    title="Detalle Cumplimiento"
    onclick="showUniqueModalFromButton(this); openGlobalModal();">
<svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2">
<path d="M3 3v18h18"></path>
<path d="M7 15l3-3 3 2 5-6"></path>
</svg>
</button>
<div class="result-filter" aria-label="Filtrar por resultado">
<button type="button" class="filter-btn active" data-result-filter="TODOS" aria-label="Todos" title="Todos">
<svg viewBox="0 0 24 24" width="17" height="17" fill="none" stroke="currentColor" stroke-width="2">
<path d="M4 6h16"></path>
<path d="M4 12h16"></path>
<path d="M4 18h16"></path>
</svg>
</button>
<button type="button" class="filter-btn" data-result-filter="SUCCESS" aria-label="SUCCESS" title="SUCCESS">
<svg viewBox="0 0 24 24" width="17" height="17" fill="none" stroke="currentColor" stroke-width="2">
<path d="M20 6 9 17l-5-5"></path>
</svg>
</button>
<button type="button" class="filter-btn" data-result-filter="WARNING" aria-label="WARNING" title="WARNING">
<svg viewBox="0 0 24 24" width="17" height="17" fill="none" stroke="currentColor" stroke-width="2">
<path d="M12 9v4"></path>
<path d="M12 17h.01"></path>
<path d="m10.29 3.86-7.1 12.29A2 2 0 0 0 4.92 19h14.16a2 2 0 0 0 1.73-2.85l-7.1-12.29a2 2 0 0 0-3.42 0z"></path>
</svg>
</button>
<button type="button" class="filter-btn" data-result-filter="FAIL" aria-label="FAIL" title="FAIL">
<svg viewBox="0 0 24 24" width="17" height="17" fill="none" stroke="currentColor" stroke-width="2">
<path d="M18 6 6 18"></path>
<path d="m6 6 12 12"></path>
</svg>
</button>
</div>
</div>
</div>
<div class="table-responsive">
<table id="myTable" class="report-table table-view-func">
<thead>
<tr>
<th>Cod. Test</th>
<th>Escenario</th>
{"".join([f"<th class='col-func'>{html.escape(c)}</th>" for c in FUNCIONALIDADES_COLUMNAS_REPORTE])}
{"".join([f"<th class='col-clas'>{html.escape(c)}</th>" for c in metricas_COLUMNAS_REPORTE])}
<th class='col-clas'>Puntuación</th>
<th>Tiempo Ejecución</th>
<th class='col-func'>Resultado</th>
<th class='col-clas'>Resultado</th>
<th>Acciones</th>
</tr>
</thead>
<tbody>
               {''.join(html_tablerows)}
</tbody>
</table>
</div>
<div class="table-controls">
<div id="tableInfo" class="table-info">Mostrando 0 de 0</div>
<div id="tablePagination" class="table-pagination" aria-label="Paginacion"></div>
</div>
</div>
"""

# =========================================... de Erwin Torres
# Erwin Torres

# ========================================================================================
promedio_score_func = round(df["score_total"].mean(), 2) if "score_total" in df.columns and len(df) > 0 else 0.0
promedio_score_metricas = (
    round(df["score_total_metricas"].mean(), 2)
    if "score_total_metricas" in df.columns and len(df) > 0
    else 0.0
)
date_str = datetime.now().strftime("%d%m%Y_%H%M%S")

tres_card_html = f"""
<div class="premium-stats-grid">
<div class="premium-card">
<div class="premium-card-icon icon-total">🪄</div>
<div class="premium-card-label">Total Casos</div>
<div class="premium-card-value">{total_cases}</div>
<div class="premium-card-sub">Escenarios evaluados</div>
</div>
<div class="summary-switcher-wrap">
<div class="summary-switcher">
<button type="button" class="summary-switch-btn is-active" data-summary-target="funcionalidades">Funcionalidades</button>
<button type="button" class="summary-switch-btn" data-summary-target="metricas">Métricas</button>
</div>

<div class="summary-group is-active" data-summary-panel="funcionalidades">
<div class="premium-card">
<div class="premium-card-icon icon-pass">✅</div>
<div class="premium-card-label">PASS</div>
<div class="premium-card-value value-pass">{total_pass_func}</div>
<div class="premium-card-sub">{pass_percent_func}% del total</div>
</div>
<div class="premium-card">
<div class="premium-card-icon icon-warning">⚠️</div>
<div class="premium-card-label">WARNING</div>
<div class="premium-card-value value-warning">{total_warning_func}</div>
<div class="premium-card-sub">{warning_percent_func}% del total</div>
</div>
<div class="premium-card">
<div class="premium-card-icon icon-fail">❌</div>
<div class="premium-card-label">FAIL</div>
<div class="premium-card-value value-fail">{total_fail_func}</div>
<div class="premium-card-sub">{fail_percent_func}% del total</div>
</div>
</div>

<div class="summary-group" data-summary-panel="metricas">
<div class="premium-card">
<div class="premium-card-icon icon-pass">✅</div>
<div class="premium-card-label">PASS</div>
<div class="premium-card-value value-pass">{total_pass_metricas}</div>
<div class="premium-card-sub">{pass_percent_metricas}% del total</div>
</div>
<div class="premium-card">
<div class="premium-card-icon icon-warning">⚠️</div>
<div class="premium-card-label">WARNING</div>
<div class="premium-card-value value-warning">{total_warning_metricas}</div>
<div class="premium-card-sub">{warning_percent_metricas}% del total</div>
</div>
<div class="premium-card">
<div class="premium-card-icon icon-fail">❌</div>
<div class="premium-card-label">FAIL</div>
<div class="premium-card-value value-fail">{total_fail_metricas}</div>
<div class="premium-card-sub">{fail_percent_metricas}% del total</div>
</div>
</div>
</div>

<div class="premium-card premium-card-score">
<div class="premium-card-icon icon-score">📊</div>
<div class="premium-card-label premium-white">
<span class="prom-label" data-prom-panel="funcionalidades">Promedio Funcionalidades</span>
<span class="prom-label" data-prom-panel="metricas">Promedio métricas</span>
</div>
<div class="premium-card-value premium-white">
<span class="prom-value" data-prom-panel="funcionalidades">{promedio_score_func:.2f}</span>
<span class="prom-value" data-prom-panel="metricas">{promedio_score_metricas:.2f}</span>
</div>
<div class="premium-card-sub premium-white-soft">
<span class="prom-sub" data-prom-panel="funcionalidades">Puntuación promedio de funcionalidades</span>
<span class="prom-sub" data-prom-panel="metricas">Puntuación promedio de métricas</span>
</div>
</div>
</div>
"""
# ========================================================================================


cabecera_html = f"""
<div class="premium-header-wrap">
<div class="premium-header">
<div>
<h2 class="premium-header-title">Reporte de Evaluación de Agente Phoenix</h2>
<div class="premium-header-sub">
               Generado: {datetime.now().strftime('%d-%m-%Y %H:%M:%S')} &nbsp;|&nbsp; Umbral Global: 80% &nbsp;|&nbsp; Casos De Prueba: {total_cases} &nbsp;|&nbsp; Tiempo de Ejecución: {wall_exec_time_formatted}
</div>
</div>
</div>
</div>
"""

html_doc = f"""
<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Reporte USER-SIMULATOR + Juez LLM</title>
<style>
   :root {{
       --bg-1: #f4f7fc;
       --bg-2: #e9eef8;
       --ink: #0f172a;
       --muted: #64748b;
       --line: #e5e7eb;
       --blue-1: #1d4ed8;
       --blue-2: #3b82f6;
       --green-1: #16a34a;
       --green-2: #22c55e;
       --red-1: #dc2626;
       --red-2: #ef4444;
   }}
   html, body {{
       min-height: 100%;
       overflow-x: hidden;
   }}
   *,
   *::before,
   *::after {{
       box-sizing: border-box;
   }}
   body {{
       font-family: "Segoe UI", Arial, sans-serif;
       margin: 0;
       padding: 24px 24px 100px 24px;
       background: linear-gradient(180deg, var(--bg-1) 0%, var(--bg-2) 100%);
       color: #1f2937;
   }}
   .page-container {{
       width: min(100%, 1540px);
       max-width: 1540px;
       margin: auto;
   }}
   .premium-header-wrap {{
       margin: 12px 0 26px 0;
   }}
   .premium-header {{
       background: linear-gradient(90deg, #185A98 0%, #3269a8 100%);
       border-radius: 24px;
       padding: 28px 34px;
       box-shadow: 0 14px 34px rgba(24, 90, 152, 0.20);
   }}
   .premium-header-title {{
       color: white;
       font-weight: 800;
       font-size: 26px;
       margin: 0 0 8px 0;
   }}
   .premium-header-sub {{
       color: #e3eafd;
       font-size: 14px;
       overflow-wrap: anywhere;
   }}
   .premium-stats-grid {{
       display: grid;
       grid-template-columns: repeat(auto-fit, minmax(190px, 1fr));
       gap: 16px;
       margin: 24px 0 26px 0;
   }}
   .summary-switcher-wrap {{
       grid-column: span 2;
       display: flex;
       flex-direction: column;
       gap: 12px;
   }}
   .summary-switcher {{
       display: inline-flex;
       gap: 8px;
       background: #eef4ff;
       border: 1px solid #dbe3ef;
       border-radius: 12px;
       padding: 6px;
       width: fit-content;
   }}
   .summary-switch-btn {{
       border: 0;
       border-radius: 8px;
       background: transparent;
       color: #1e3a8a;
       font-size: 13px;
       font-weight: 800;
       padding: 8px 12px;
       cursor: pointer;
   }}
   .summary-switch-btn.is-active {{
       background: white;
       box-shadow: 0 4px 10px rgba(15, 23, 42, 0.08);
   }}
   .summary-group {{
       display: none;
       gap: 16px;
       grid-template-columns: repeat(3, minmax(180px, 1fr));
   }}
   .summary-group.is-active {{
       display: grid;
   }}
   .premium-card {{
       background: rgba(255,255,255,0.97);
       border-radius: 22px;
       padding: 22px;
       min-height: 150px;
       box-shadow: 0 10px 26px rgba(15, 23, 42, 0.08);
       position: relative;
       overflow: hidden;
       border: 1px solid #edf1f7;
       display: flex;
       flex-direction: column;
       justify-content: center;
       min-width: 0;
   }}
   .premium-card::after {{
       content: "";
       position: absolute;
       width: 86px;
       height: 86px;
       right: -20px;
       bottom: -20px;
       border-radius: 50%;
       background: rgba(148, 163, 184, 0.08);
   }}
   .premium-card-icon {{
       width: 54px;
       height: 54px;
       border-radius: 16px;
       display: flex;
       align-items: center;
       justify-content: center;
       font-size: 27px;
       margin-bottom: 14px;
   }}
   .icon-total {{
       background: linear-gradient(135deg, #fef3c7, #fde68a);
   }}
   .icon-pass {{
       background: linear-gradient(135deg, #dcfce7, #86efac);
   }}
   .icon-fail {{
       background: linear-gradient(135deg, #fee2e2, #fca5a5);
   }}
   .icon-warning {{
       background: linear-gradient(135deg, #fef3c7, #f59e0b);
   }}
   .icon-score {{
       background: rgba(255,255,255,0.18);
       color: white;
   }}
   .premium-card-label {{
       font-size: 17px;
       color: #64748b;
       margin-bottom: 8px;
   }}
   .premium-card-value {{
       font-size: 46px;
       font-weight: 800;
       line-height: 1.05;
       color: #0f172a;
   }}
   .premium-card-sub {{
       margin-top: 8px;
       font-size: 14px;
       color: #64748b;
   }}
   .value-pass {{
       color: #16a34a;
   }}
   .value-fail {{
       color: #dc2626;
   }}
   .value-warning {{
       color: #b45309;
   }}
   .premium-card-score {{
       background: linear-gradient(135deg, #2563eb, #3b82f6);
       color: white;
   }}
   .premium-white {{
       color: white;
   }}
   .premium-white-soft {{
       color: rgba(255,255,255,0.90);
   }}
   .prom-label,
   .prom-value,
   .prom-sub {{
       display: none;
   }}
   .prom-label.is-active,
   .prom-value.is-active,
   .prom-sub.is-active {{
       display: inline;
   }}
   .premium-card-donut {{
       display: flex;
       align-items: center;
       justify-content: center;
   }}
   .donut-wrap {{
       display: flex;
       align-items: center;
       gap: 18px;
   }}
   .donut-chart {{
       width: 96px;
       height: 96px;
       border-radius: 50%;
       position: relative;
       flex-shrink: 0;
   }}
   .donut-chart::after {{
       content: "";
       position: absolute;
       inset: 18px;
       background: white;
       border-radius: 50%;
   }}
   .donut-center {{
       position: absolute;
       inset: 0;
       z-index: 2;
       display: flex;
       align-items: center;
       justify-content: center;
       font-weight: 800;
       font-size: 18px;
       color: #0f172a;
   }}
   .donut-legend {{
       font-size: 14px;
       color: #475569;
       display: flex;
       flex-direction: column;
       gap: 8px;
   }}
   .dot {{
       width: 11px;
       height: 11px;
       display: inline-block;
       border-radius: 999px;
       margin-right: 8px;
   }}
   .dot-pass {{
       background: #16a34a;
   }}
   .dot-fail {{
       background: #ef4444;
   }}
   .table-card {{
       background: rgba(255,255,255,0.98);
       border-radius: 24px;
       overflow: hidden;
       box-shadow: 0 14px 34px rgba(15, 23, 42, 0.08);
       padding: 0;
       margin-bottom: 32px;
       max-width: 100%;
   }}
   .table-title {{
       padding: 0;
       font-size: 20px;
       font-weight: 800;
       color: #1e3a8a;
   }}
   .table-card-header {{
       display: flex;
       align-items: center;
       justify-content: space-between;
       gap: 16px;
       padding: 18px 24px 12px 24px;
   }}
   .table-header-actions {{
       display: flex;
       align-items: center;
       justify-content: flex-end;
       gap: 12px;
       flex-wrap: wrap;
   }}
   .result-filter {{
       display: flex;
       gap: 10px;
       align-items: center;
       justify-content: flex-end;
       flex-wrap: wrap;
   }}
   .summary-modal-btn {{
       border: 1px solid #dbe3ef;
       border-radius: 12px;
       background: white;
       color: #174ea6;
       cursor: pointer;
       display: inline-flex;
       align-items: center;
       justify-content: center;
       width: 48px;
       height: 42px;
       padding: 0;
       box-shadow: 0 8px 18px rgba(15, 23, 42, 0.06);
       transition: all .18s ease;
   }}
   .summary-modal-btn svg,
   .filter-btn svg {{
       pointer-events: none;
   }}
   .summary-modal-btn:hover {{
       background: #f8fbff;
       border-color: #b8c9e6;
       box-shadow: 0 10px 24px rgba(30, 64, 175, 0.10);
   }}
   .filter-btn {{
       border: 1px solid #dbe3ef;
       border-radius: 12px;
       background: white;
       color: #0f172a;
       cursor: pointer;
       display: inline-flex;
       align-items: center;
       justify-content: center;
       width: 48px;
       height: 42px;
       min-width: 0;
       padding: 0;
       box-shadow: 0 8px 18px rgba(15, 23, 42, 0.06);
       transition: all .18s ease;
   }}
   .filter-btn:hover,
   .filter-btn.active {{
       background: #f8fbff;
       border-color: #b8c9e6;
       color: #174ea6;
       box-shadow: 0 10px 24px rgba(30, 64, 175, 0.10);
   }}
   .table-responsive {{
       width: 100%;
       overflow-x: auto;
       -webkit-overflow-scrolling: touch;
       overscroll-behavior-x: contain;
       scrollbar-gutter: stable;
   }}
   #myTable {{
       width: 100% !important;
       min-width: 1540px;
       background: transparent;
       border-collapse: separate;
       border-spacing: 0;
   }}
   #myTable thead th {{
       background: linear-gradient(180deg, #f8fbff 0%, #eef4ff 100%);
       color: #0f172a;
       font-weight: 800;
       font-size: 12px !important;
       text-transform: uppercase;
       border-bottom: 1px solid #e5e7eb !important;
       border-top: none !important;
   }}
   #myTable td {{
       font-size: 13px !important;
       color: #334155;
       vertical-align: middle;
       border-bottom: 1px solid #eef2f7 !important;
   }}
   #myTable th, #myTable td {{
       padding: 14px 12px !important;
   }}
   #myTable.table-view-func .col-clas {{
       display: none;
   }}
   #myTable.table-view-clas .col-func {{
       display: none;
   }}
   .td-exec-time {{
       font-family: "Consolas", "Courier New", monospace;
       font-weight: 700;
       color: #0f172a;
       white-space: nowrap;
   }}
   .td-ellipsis {{
       max-width: 220px;
       white-space: nowrap;
       overflow: hidden;
       text-overflow: ellipsis;
   }}
   .badge-pass {{
       display: inline-block;
       padding: 7px 14px;
       border-radius: 999px;
       background: linear-gradient(135deg, #16a34a, #22c55e);
       color: white;
       font-weight: 800;
       font-size: 12px;
   }}
   .badge-fail {{
       display: inline-block;
       padding: 7px 14px;
       border-radius: 999px;
       background: linear-gradient(135deg, #dc2626, #ef4444);
       color: white;
       font-weight: 800;
       font-size: 12px;
   }}
   .badge-warning {{
       display: inline-block;
       padding: 7px 14px;
       border-radius: 999px;
       background: linear-gradient(135deg, #d97706, #f59e0b);
       color: white;
       font-weight: 800;
       font-size: 12px;
   }}
   .score-wrap {{
       display: flex;
       flex-direction: column;
       gap: 6px;
       align-items: center;
   }}
   .score-pass {{
       color: #15803d;
       font-weight: 800;
       font-size: 28px;
   }}
   .score-fail {{
       color: #b91c1c;
       font-weight: 800;
       font-size: 28px;
   }}
   .score-warning {{
       color: #b45309;
       font-weight: 800;
       font-size: 28px;
   }}
   .score-bar {{
       width: 74px;
       height: 8px;
       border-radius: 999px;
       background: #e5e7eb;
       overflow: hidden;
   }}
   .score-fill {{
       height: 100%;
       border-radius: 999px;
   }}
   .fill-pass {{
       background: linear-gradient(135deg, #16a34a, #22c55e);
   }}
   .fill-warning {{
       background: linear-gradient(135deg, #d97706, #f59e0b);
   }}
   .fill-fail {{
       background: linear-gradient(135deg, #dc2626, #ef4444);
   }}
   .action-group {{
       display: flex;
       gap: 8px;
       justify-content: center;
       flex-wrap: wrap;
   }}
   .icon-btn {{
       width: 38px;
       height: 38px;
       border-radius: 12px;
       border: 1px solid #dbe3ef;
       background: white;
       color: #1e3a8a;
       display: inline-flex;
       align-items: center;
       justify-content: center;
       cursor: pointer;
       transition: all .18s ease;
       box-shadow: 0 6px 16px rgba(15, 23, 42, 0.06);
   }}
   .icon-btn:hover {{
       transform: translateY(-1px);
       background: #eef4ff;
       border-color: #bfd4ff;
   }}
   .modal {{
       position: fixed;
       inset: 0;
       display: none;
       align-items: center;
       justify-content: center;
       padding: clamp(14px, 3vw, 32px);
       z-index: 2000;
   }}
   body.modal-open {{
       overflow: hidden;
   }}
   .modal.is-open {{
       display: flex;
   }}
   .modal-backdrop {{
       position: absolute;
       inset: 0;
       background: rgba(15, 23, 42, 0.55);
   }}
   .modal-dialog {{
       position: relative;
       z-index: 1;
       width: min(1240px, 96vw);
       height: min(820px, calc(100dvh - 64px));
       max-height: calc(100dvh - 64px);
       display: flex;
   }}
   .modal-content {{
       width: 100%;
       height: 100%;
       max-height: 100%;
       display: flex;
       flex-direction: column;
       border-radius: 22px;
       border: none;
       box-shadow: 0 22px 60px rgba(15, 23, 42, 0.18);
       overflow: hidden;
   }}
   .modal-header {{
       background: linear-gradient(90deg, #185A98 0%, #3269a8 100%);
       color: white;
       border-bottom: none;
       padding: 18px 22px;
       display: flex;
       align-items: center;
       justify-content: space-between;
       gap: 16px;
   }}
   .modal-title {{
       font-weight: 800;
       font-size: 20px;
   }}
   .btn-close {{
       width: 34px;
       height: 34px;
       border: 0;
       border-radius: 10px;
       background: rgba(255,255,255,0.18);
       color: white;
       cursor: pointer;
       display: inline-flex;
       align-items: center;
       justify-content: center;
       font-size: 24px;
       line-height: 1;
   }}
   .modal-body {{
       flex: 1;
       min-height: 0;
       padding: 0;
       background: #f8fbff;
       overflow: hidden;
   }}
   .modal-viewer {{
       box-sizing: border-box;
       display: block;
       width: 100%;
       height: 100%;
       min-height: 0;
       margin: 0;
       border-radius: 0;
       border: 0;
       background: white;
       color: #334155;
       font-family: Consolas, Monaco, monospace;
       font-size: 13px;
       line-height: 1.65;
       padding: 22px;
       outline: none;
       white-space: pre-wrap;
       overflow: auto;
       scrollbar-gutter: stable;
       tab-size: 2;
   }}
   .modal-footer {{
       border-top: 1px solid #e5e7eb;
       background: white;
       padding: 14px 22px;
       display: flex;
       gap: 10px;
       justify-content: flex-end;
   }}
   .modal-back-btn {{
       border: 1px solid #dbe3ef;
       border-radius: 10px;
       background: white;
       color: #174ea6;
       cursor: pointer;
       display: none;
       font-weight: 800;
       padding: 10px 18px;
   }}
   .modal-back-btn.is-visible {{
       display: inline-flex;
       align-items: center;
       justify-content: center;
   }}
   .modal-back-btn:hover {{
       background: #eef4ff;
       border-color: #b8c9e6;
   }}
   .modal-close-btn {{
       border: 0;
       border-radius: 10px;
       background: #334155;
       color: white;
       cursor: pointer;
       font-weight: 800;
       padding: 10px 18px;
   }}
   .footer-fixed {{
       position: fixed;
       left: 24px;
       right: 24px;
       bottom: 12px;
       background: rgba(255,255,255,0.98);
       border: 1px solid #e5e7eb;
       border-radius: 16px;
       padding: 14px 18px;
       text-align: center;
       font-size: 13px;
       color: #475569;
       box-shadow: 0 10px 28px rgba(15, 23, 42, 0.08);
       z-index: 999;
   }}
   .footer-fixed strong {{
       color: #0f172a;
   }}
   .table-controls {{
       display: flex;
       align-items: center;
       justify-content: space-between;
       gap: 12px;
       border-top: 1px solid #e5e7eb;
       padding: 12px 18px 18px 18px;
   }}
   .table-info {{
       font-size: 12px;
       color: #64748b;
   }}
   .table-pagination {{
       display: flex;
       align-items: center;
       justify-content: flex-end;
       gap: 6px;
       flex-wrap: wrap;
   }}
   .table-page-btn {{
       border-radius: 10px;
       border: 1px solid #dbe3ef;
       background: white;
       color: #334155;
       cursor: pointer;
       font-size: 12px;
       font-weight: 700;
       min-width: 36px;
       padding: 8px 10px;
   }}
   .table-page-btn.is-active {{
       background: linear-gradient(135deg, #2563eb, #3b82f6);
       color: white;
       border-color: transparent;
   }}
   .table-page-btn:disabled {{
       cursor: not-allowed;
       opacity: .45;
   }}
   @media (max-width: 1300px) {{
       .premium-stats-grid {{
           grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
       }}
   }}
   @media (max-width: 768px) {{
       .premium-stats-grid {{
           grid-template-columns: 1fr;
       }}
       .page-container {{
           width: 100%;
       }}
       .premium-header-wrap {{
           margin: 6px 0 16px 0;
       }}
       .premium-header {{
           border-radius: 18px;
           padding: 20px 18px;
       }}
       .premium-header-title {{
           font-size: 20px;
           line-height: 1.25;
       }}
       .premium-header-sub {{
           font-size: 12px;
           line-height: 1.6;
       }}
       .premium-card {{
           border-radius: 16px;
           min-height: 118px;
           padding: 18px;
       }}
       .premium-card-icon {{
           width: 44px;
           height: 44px;
           border-radius: 12px;
           font-size: 22px;
           margin-bottom: 10px;
       }}
       .premium-card-label {{
           font-size: 14px;
       }}
       .premium-card-value {{
           font-size: 34px;
       }}
       .donut-wrap {{
           flex-direction: column;
           align-items: flex-start;
       }}
       body {{
           padding: 12px 12px 24px 12px;
       }}
       .table-card {{
           border-radius: 18px;
       }}
       .table-title {{
           font-size: 18px;
       }}
       .footer-fixed {{
           position: static;
           margin-top: 18px;
           border-radius: 14px;
           padding: 12px;
           line-height: 1.5;
       }}
       .table-card-header,
       .table-controls {{
           align-items: stretch;
           flex-direction: column;
       }}
       .table-header-actions {{
           align-items: center;
           justify-content: flex-start;
       }}
       .summary-modal-btn {{
           flex: 0 0 48px;
           width: 48px;
       }}
       .result-filter {{
           display: grid;
           grid-template-columns: repeat(4, 48px);
           width: auto;
       }}
       .filter-btn {{
           width: 48px;
           padding: 0;
       }}
       .result-filter,
       .table-pagination {{
           justify-content: flex-start;
       }}
       .table-responsive {{
           overflow-x: visible;
           padding: 0 12px 12px 12px;
       }}
       #myTable {{
           min-width: 0;
           border-collapse: separate;
           border-spacing: 0 12px;
       }}
       #myTable thead {{
           display: none;
       }}
       #myTable tbody,
       #myTable tr,
       #myTable td {{
           display: block;
           width: 100%;
       }}
       #myTable tr {{
           background: white;
           border: 1px solid #e5e7eb;
           border-radius: 16px;
           box-shadow: 0 8px 22px rgba(15, 23, 42, 0.06);
           padding: 12px;
       }}
       #myTable td {{
           display: grid;
           grid-template-columns: minmax(118px, 42%) minmax(0, 1fr);
           align-items: center;
           gap: 10px;
           min-height: 44px;
           padding: 10px 0 !important;
           text-align: right;
           border-bottom: 1px solid #eef2f7 !important;
       }}
       #myTable td:last-child {{
           border-bottom: 0 !important;
       }}
       #myTable td::before {{
           content: attr(data-label);
           color: #0f172a;
           font-size: 12px;
           font-weight: 900;
           line-height: 1.3;
           text-align: left;
           text-transform: uppercase;
       }}
       .td-ellipsis {{
           max-width: none;
           white-space: normal;
       }}
       .score-wrap {{
           align-items: flex-end;
       }}
       .score-pass,
       .score-fail {{
           font-size: 22px;
       }}
       .action-group {{
           justify-content: flex-end;
       }}
       .table-controls {{
           padding: 12px;
       }}
       .table-pagination {{
           gap: 5px;
       }}
       .table-page-btn {{
           flex: 1 1 auto;
           min-width: 42px;
       }}
       .modal {{
           align-items: stretch;
           padding: 8px;
       }}
       .modal-dialog {{
           width: 100%;
           height: calc(100dvh - 16px);
           max-height: calc(100dvh - 16px);
       }}
       .modal-content {{
           border-radius: 16px;
       }}
       .modal-header {{
           padding: 14px 16px;
       }}
       .modal-title {{
           font-size: 17px;
           line-height: 1.25;
       }}
       .modal-viewer,
       .modal-rich-content {{
           padding: 14px;
       }}
       .modal-footer {{
           padding: 12px 14px;
       }}
       .modal-back-btn,
       .modal-close-btn {{
           flex: 1 1 0;
           width: auto;
       }}
       .conversation-thread {{
           max-width: none;
       }}
       .conversation-text,
       .metric-card-desc,
       .metric-summary-text {{
           font-size: 13px;
       }}
       .compliance-table {{
           min-width: 940px;
       }}
       .scenario-functionality-table {{
           min-width: 680px;
       }}
   }}
   @media (max-width: 420px) {{
       .premium-header {{
           padding: 18px 14px;
       }}
       .result-filter {{
           grid-template-columns: repeat(4, 48px);
       }}
       #myTable td {{
           grid-template-columns: 1fr;
           text-align: left;
       }}
       .score-wrap,
       .action-group {{
           align-items: flex-start;
           justify-content: flex-start;
       }}
       .score-bar {{
           width: 100%;
       }}
       .donut-chart {{
           width: 84px;
           height: 84px;
       }}
       .modal-header {{
           gap: 10px;
       }}
       .btn-close {{
           flex: 0 0 auto;
       }}
   }}



   .modal-rich-content {{
       box-sizing: border-box;
       height: 100%;
       overflow: auto;
       padding: 22px;
       background: #f8fbff;
       scrollbar-gutter: stable;
   }}
   .conversation-thread {{
       display: flex;
       flex-direction: column;
       gap: 14px;
       max-width: 980px;
       margin: 0 auto;
   }}
   .conversation-message {{
       border: 1px solid #dbe3ef;
       border-radius: 16px;
       background: white;
       box-shadow: 0 8px 22px rgba(15, 23, 42, 0.06);
       padding: 14px 16px;
   }}
   .conversation-message.client {{
       border-left: 5px solid #2563eb;
   }}
   .conversation-message.bot {{
       border-left: 5px solid #16a34a;
   }}
   .conversation-role {{
       color: #0f172a;
       font-size: 12px;
       font-weight: 900;
       letter-spacing: .02em;
       margin-bottom: 8px;
       text-transform: uppercase;
   }}
   .conversation-text {{
       color: #334155;
       font-size: 14px;
       line-height: 1.7;
       white-space: pre-wrap;
   }}
   .data-panel {{
       height: 100%;
       background: white;
       border: 1px solid #dbe3ef;
       border-radius: 16px;
       box-shadow: 0 8px 22px rgba(15, 23, 42, 0.06);
       overflow: hidden;
   }}
   .data-pre {{
       box-sizing: border-box;
       height: 100%;
       margin: 0;
       overflow: auto;
       padding: 20px;
       color: #1f2937;
       font-family: Consolas, Monaco, monospace;
       font-size: 13px;
       line-height: 1.65;
       white-space: pre;
       scrollbar-gutter: stable;
   }}
.compliance-panel {{
   background: white;
   border: 1px solid #dbe3ef;
   border-radius: 16px;
   box-shadow: 0 8px 22px rgba(15, 23, 42, 0.06);
   overflow: hidden;
}}
.compliance-table-scroll {{
   width: 100%;
   overflow: auto;
}}
.compliance-table {{
   width: 100%;
   min-width: 1040px;
   border-collapse: collapse;
   background: white;
}}
.compliance-table th,
.compliance-table td {{
   border: 1px solid #e5e7eb;
   padding: 11px 12px;
   color: #334155;
   font-size: 13px;
   text-align: center;
}}
.compliance-table th {{
   background: linear-gradient(180deg, #f8fbff 0%, #eef4ff 100%);
   color: #0f172a;
   font-weight: 900;
   text-transform: uppercase;
}}
.compliance-table td:first-child {{
   color: #0f172a;
   font-weight: 800;
   text-align: left;
}}
.compliance-table .compliance-count {{
   font-weight: 900;
}}
.compliance-table .compliance-total {{
   background: #f8fafc;
   color: #0f172a;
   font-weight: 900;
}}
.compliance-count-btn {{
   width: 100%;
   min-width: 42px;
   border: 0;
   border-radius: 8px;
   background: #eef4ff;
   color: #174ea6;
   cursor: pointer;
   font-size: 13px;
   font-weight: 900;
   padding: 7px 8px;
   transition: all .18s ease;
}}
.compliance-count-btn:hover {{
   background: #dbeafe;
   box-shadow: inset 0 0 0 1px #b8c9e6;
}}
.scenario-functionality-head {{
   margin-bottom: 14px;
   color: #0f172a;
   font-size: 16px;
   font-weight: 900;
}}
.scenario-functionality-table {{
   min-width: 780px;
   table-layout: fixed;
}}
.scenario-functionality-table td {{
   vertical-align: top;
   text-align: left;
   line-height: 1.55;
}}
.scenario-functionality-table td:first-child {{
   width: 120px;
   white-space: nowrap;
}}
.scenario-functionality-table td:nth-child(2) {{
   width: 34%;
}}
.scenario-functionality-table th:first-child {{
   width: 120px;
}}
.scenario-functionality-table th:nth-child(2) {{
   width: 34%;
}}
.scenario-text-ellipsis {{
   cursor: help;
   display: block;
   max-width: 100%;
   overflow: hidden;
   text-overflow: ellipsis;
   white-space: nowrap;
}}
.metric-cards-grid {{
   display: grid;
   grid-template-columns: repeat(2, 1fr);
   gap: 14px;
}}
.metric-tabs-wrapper {{
    display: flex;
    flex-direction: column;
    gap: 14px;
}}
.metric-tabs {{
    display: inline-flex;
    gap: 8px;
    background: #eef4ff;
    border: 1px solid #dbe3ef;
    border-radius: 12px;
    padding: 6px;
    width: fit-content;
}}
.metric-tab-btn {{
    border: 0;
    border-radius: 8px;
    background: transparent;
    color: #1e3a8a;
    font-size: 13px;
    font-weight: 800;
    padding: 8px 12px;
    cursor: pointer;
}}
.metric-tab-btn.is-active {{
    background: white;
    box-shadow: 0 4px 10px rgba(15, 23, 42, 0.08);
}}
.metric-tab-panel {{
    display: none;
}}
.metric-tab-panel.is-active {{
    display: block;
}}
.metric-card {{
   background: white;
   border: 1px solid #dbe3ef;
   border-radius: 18px;
   padding: 16px;
   box-shadow: 0 8px 18px rgba(15, 23, 42, 0.05);
}}
.metric-card-header {{
   display: flex;
   justify-content: space-between;
   align-items: center;
   margin-bottom: 10px;
}}
.metric-card-title {{
   font-size: 16px;
   font-weight: 800;
   color: #0f172a;
}}
.metric-card-score {{
   background: #e0e7ff;
   color: #1d4ed8;
   border-radius: 999px;
   padding: 5px 10px;
   font-size: 13px;
   font-weight: 800;
}}
.metric-card-desc {{
   font-size: 14px;
   color: #475569;
   line-height: 1.6;
}}
.metric-summary-box {{
   margin-top: 18px;
   background: #f8fbff;
   border: 1px solid #dbe3ef;
   border-radius: 16px;
   padding: 16px;
}}
.metric-summary-title {{
   font-size: 15px;
   font-weight: 800;
   color: #0f172a;
   margin-bottom: 8px;
}}
.metric-summary-text {{
   font-size: 14px;
   color: #475569;
   line-height: 1.7;
}}
@media (max-width: 900px) {{
   .metric-cards-grid {{
       grid-template-columns: 1fr;
   }}
}}



.metric-score-line {{
    font-size: 14px;
    color: #334155;
    margin-bottom: 10px;
}}



.metric-justification {{
    font-size: 13px;
    line-height: 1.6;
    color: #475569;
    background: #f8fafc;
    border-radius: 12px;
    padding: 12px;
    border: 1px solid #e5e7eb;
}}



.badge-cumple {{
    display: inline-block;
    padding: 6px 10px;
    border-radius: 999px;
    background: linear-gradient(135deg, #16a34a, #22c55e);
    color: white;
    font-weight: 800;
    font-size: 10px;
    white-space: nowrap;
}}



.badge-no-cumple {{
    display: inline-block;
    padding: 6px 10px;
    border-radius: 999px;
    background: linear-gradient(135deg, #dc2626, #ef4444);
    color: white;
    font-weight: 800;
    font-size: 10px;
    white-space: nowrap;
}}



.badge-no-aplica {{
    display: inline-block;
    padding: 6px 10px;
    border-radius: 999px;
    background: linear-gradient(135deg, #f59e0b, #fbbf24);
    color: #78350f;
    font-weight: 800;
    font-size: 10px;
    white-space: nowrap;
}}

.badge-metrica {{
    display: inline-block;
    padding: 6px 10px;
    border-radius: 999px;
    color: white;
    font-weight: 800;
    font-size: 11px;
    white-space: nowrap;
    min-width: 52px;
    text-align: center;
}}

.badge-metrica-pass {{
    background: linear-gradient(135deg, #16a34a, #22c55e);
}}

.badge-metrica-warning {{
    background: linear-gradient(135deg, #d97706, #f59e0b);
}}

.badge-metrica-fail {{
    background: linear-gradient(135deg, #dc2626, #ef4444);
}}



.metric-card-score.badge-modal-cumple {{
    background: linear-gradient(135deg, #16a34a, #22c55e);
    color: white;
}}



.metric-card-score.badge-modal-no-cumple {{
    background: linear-gradient(135deg, #dc2626, #ef4444);
    color: white;
}}



.metric-card-score.badge-modal-no-aplica {{
    background: linear-gradient(135deg, #f59e0b, #fbbf24);
    color: #78350f;
}}

.metric-card-score.badge-modal-warning {{
    background: linear-gradient(135deg, #d97706, #f59e0b);
    color: white;
}}


@media (max-width: 768px) {{
   .modal-rich-content {{
       padding: 14px;
   }}
   .modal-viewer,
   .data-pre {{
       padding: 14px;
       font-size: 12px;
   }}
   .conversation-thread {{
       max-width: none;
   }}
   .conversation-message {{
       border-radius: 14px;
       padding: 12px;
   }}
   .conversation-text,
   .metric-card-desc,
   .metric-summary-text {{
       font-size: 13px;
   }}
   .metric-card {{
       border-radius: 14px;
       padding: 14px;
   }}
   .metric-card-header {{
       align-items: flex-start;
       flex-direction: column;
       gap: 8px;
   }}
   .metric-card-score {{
       align-self: flex-start;
   }}
   .metric-summary-box {{
       border-radius: 14px;
       padding: 14px;
   }}
   .compliance-table {{
       min-width: 940px;
   }}
   .scenario-functionality-table {{
       min-width: 680px;
   }}
   .compliance-table th,
   .compliance-table td {{
       font-size: 12px;
       padding: 9px 10px;
   }}
}}

@media (max-width: 420px) {{
   .compliance-table {{
       min-width: 860px;
   }}
   .scenario-functionality-table {{
       min-width: 620px;
   }}
}}



</style>
{html_modal_contents}
</head>
<body>
<div class="page-container">
   {cabecera_html}
   {tres_card_html}
   {html_table}
</div>

<div class="modal" id="uniqueGlobalModal" role="dialog" aria-modal="true" aria-labelledby="uniqueModalTitle" aria-hidden="true">
   <div class="modal-backdrop" onclick="closeGlobalModal()"></div>
   <div class="modal-dialog">
      <div class="modal-content">
         <div class="modal-header">
            <h5 class="modal-title" id="uniqueModalTitle">Detalle</h5>
            <button type="button" class="btn-close" onclick="closeGlobalModal()" aria-label="Cerrar">&times;</button>
         </div>
         <div class="modal-body">
            <div id="uniqueModalRichContent" class="modal-rich-content" style="display:none;"></div>
            <pre id="uniqueModalTextContent" class="modal-viewer"></pre>
         </div>
         <div class="modal-footer">
            <button type="button" class="modal-back-btn" id="modalBackToComplianceBtn" onclick="volverDetalleCumplimiento()">Volver</button>
            <button type="button" class="modal-close-btn" onclick="closeGlobalModal()">Cerrar</button>
         </div>
      </div>
   </div>
</div>

<div class="footer-fixed">
   Programa IA Credicorp | Área de Quality Engineer | Squad de Agente |
<strong>© 2026 Todos los Derechos Reservados.</strong>
</div>

<script>
function escaparHtml(texto) {{
   if (texto === null || texto === undefined) return "";
   return String(texto)
       .replace(/&/g, "&amp;")
       .replace(/</g, "&lt;")
       .replace(/>/g, "&gt;")
       .replace(/"/g, "&quot;")
       .replace(/'/g, "&#039;");
}}


function getTextoScore(valor) {{
   valor = Number(valor);

    if (valor >= 0.8) return "PASS";
    if (valor >= 0.5) return "WARNING";
    return "FAIL";
}}

function getClaseScore(valor) {{
   valor = Number(valor);

    if (valor >= 0.8) return "badge-modal-cumple";
    if (valor >= 0.5) return "badge-modal-warning";
    return "badge-modal-no-cumple";
}}

function formatearPorcentaje(valor) {{
   const numero = Number(valor);
   if (!Number.isFinite(numero)) return "0%";
   return new Intl.NumberFormat('es-PE', {{
       minimumFractionDigits: 0,
       maximumFractionDigits: 2
   }}).format(numero) + "%";
}}

function renderComplianceCountButton(item, estadoKey, valor, estadoLabel) {{
   const count = Number(valor || 0);
   const key = item.key || "";
   const funcionalidad = item.funcionalidad || "";

   return `
<button type="button" class="compliance-count-btn"
        data-funcionalidad-key="${{escaparHtml(key)}}"
        data-estado-key="${{escaparHtml(estadoKey)}}"
        onclick="abrirEscenariosDesdeBoton(this)"
        title="Ver escenarios ${{escaparHtml(estadoLabel)}} de ${{escaparHtml(funcionalidad)}}">
    ${{count}}
</button>
`;
}}

function abrirEscenariosDesdeBoton(btn) {{
   abrirEscenariosPorFuncionalidad(
       btn.getAttribute("data-funcionalidad-key") || "",
       btn.getAttribute("data-estado-key") || ""
   );
}}

function setModalBackButtonVisible(visible) {{
   const backBtn = document.getElementById('modalBackToComplianceBtn');
   if (!backBtn) return;
   backBtn.classList.toggle('is-visible', Boolean(visible));
}}

function volverDetalleCumplimiento() {{
   const textContent = document.getElementById('uniqueModalTextContent');
   const rich = document.getElementById('uniqueModalRichContent');
   const lbl = document.getElementById('uniqueModalTitle');

   if (!textContent || !rich || !lbl) return;

   lbl.textContent = "DETALLE CUMPLIMIENTO";
   textContent.style.display = "none";
   rich.style.display = "block";
   textContent.textContent = "";
   rich.innerHTML = renderDetalleCumplimiento(window.__DETALLE_CUMPLIMIENTO__);
   rich.scrollTop = 0;
   setModalBackButtonVisible(false);
}}

function abrirEscenariosPorFuncionalidad(funcionalidadKey, estadoKey) {{
   const textContent = document.getElementById('uniqueModalTextContent');
   const rich = document.getElementById('uniqueModalRichContent');
   const lbl = document.getElementById('uniqueModalTitle');

   if (!textContent || !rich || !lbl) return;

   const data = window.__ESCENARIOS_FUNCIONALIDAD__ || {{}};
   const funcionalidad = data[funcionalidadKey] || {{}};
   const nombreFuncionalidad = funcionalidad.label || funcionalidadKey || "Funcionalidad";

   lbl.textContent = "Escenarios Por Funcionalidad: " + nombreFuncionalidad;
   textContent.style.display = "none";
   rich.style.display = "block";
   textContent.textContent = "";
   rich.innerHTML = renderEscenariosPorFuncionalidad(funcionalidadKey, estadoKey);
   rich.scrollTop = 0;
   setModalBackButtonVisible(true);
}}

function renderEscenariosPorFuncionalidad(funcionalidadKey, estadoKey) {{
   const data = window.__ESCENARIOS_FUNCIONALIDAD__ || {{}};
   const funcionalidad = data[funcionalidadKey] || {{}};
   const estados = funcionalidad.estados || {{}};
   const estado = estados[estadoKey] || {{}};
   const escenarios = Array.isArray(estado.escenarios) ? estado.escenarios : [];
   const estadoLabel = estado.label || estadoKey || "";

   if (!escenarios.length) {{
       return `
<div class="metric-summary-box">
    <div class="metric-summary-title">Sin escenarios ${{escaparHtml(estadoLabel)}}</div>
    <div class="metric-summary-text">No se encontraron escenarios para esta funcionalidad y estado.</div>
</div>
`;
   }}

   let rows = "";
   escenarios.forEach(function(item) {{
       rows += `
<tr>
    <td>${{escaparHtml(item.id_test || "")}}</td>
    <td><span class="scenario-text-ellipsis" title="${{escaparHtml(item.escenario || "")}}">${{escaparHtml(item.escenario || "")}}</span></td>
    <td><span class="scenario-text-ellipsis" title="${{escaparHtml(item.justificacion || "")}}">${{escaparHtml(item.justificacion || "")}}</span></td>
</tr>
`;
   }});

   return `
<div class="scenario-functionality-head">${{escaparHtml(estadoLabel)}}: ${{escenarios.length}} escenario(s)</div>
<div class="compliance-panel">
    <div class="compliance-table-scroll">
        <table class="compliance-table scenario-functionality-table">
            <thead>
                <tr>
                    <th>Cod. Test</th>
                    <th>Escenario</th>
                    <th>Detalle de las métricas</th>
                </tr>
            </thead>
            <tbody>
                ${{rows}}
            </tbody>
        </table>
    </div>
</div>
`;
}}

function renderDetalleCumplimiento(data) {{
   const filas = data && Array.isArray(data.filas) ? data.filas : [];

   if (!filas.length) {{
       return `
<div class="metric-summary-box">
    <div class="metric-summary-title">Sin detalle de cumplimiento</div>
    <div class="metric-summary-text">No se encontraron escenarios ejecutados para visualizar.</div>
</div>
`;
   }}

   let rows = "";
   filas.forEach(function(item) {{
       rows += `
<tr>
    <td>${{escaparHtml(item.funcionalidad || "")}}</td>
    <td class="compliance-count">${{renderComplianceCountButton(item, "cumple", item.cumple, "Cumple")}}</td>
    <td>${{formatearPorcentaje(item.cumple_pct)}}</td>
    <td class="compliance-count">${{renderComplianceCountButton(item, "no_cumple", item.no_cumple, "No Cumple")}}</td>
    <td>${{formatearPorcentaje(item.no_cumple_pct)}}</td>
    <td class="compliance-total">${{Number(item.aplica || 0)}}</td>
    <td class="compliance-count">${{renderComplianceCountButton(item, "no_aplica", item.no_aplica, "No Aplica")}}</td>
    <td>${{formatearPorcentaje(item.no_aplica_pct)}}</td>
    <td class="compliance-count">${{renderComplianceCountButton(item, "aplica", item.aplica, "Aplica")}}</td>
    <td>${{formatearPorcentaje(item.aplica_pct)}}</td>
    <td class="compliance-total">${{Number(item.escenarios || 0)}}</td>
</tr>
`;
   }});

   return `
<div class="compliance-panel">
    <div class="compliance-table-scroll">
        <table class="compliance-table">
            <thead>
                <tr>
                    <th rowspan="3">Funcionalidad</th>
                    <th colspan="5">Aplica</th>
                    <th colspan="5">Total Casos</th>
                </tr>
                <tr>
                    <th colspan="2">Cumple</th>
                    <th colspan="2">No Cumple</th>
                    <th rowspan="2">Total</th>
                    <th colspan="2">No Aplica</th>
                    <th colspan="2">Aplica</th>
                    <th rowspan="2">Esc.</th>
                </tr>
                <tr>
                    <th>Cant.</th>
                    <th>%</th>
                    <th>Cant.</th>
                    <th>%</th>
                    <th>Cant.</th>
                    <th>%</th>
                    <th>Cant.</th>
                    <th>%</th>
                </tr>
            </thead>
            <tbody>
                ${{rows}}
            </tbody>
        </table>
    </div>
</div>
`;
}}


function renderMetricCard(item) {{

   let nombre = item.label || item.key || "";

   let valor = Number(item.score);

   let estado = item.estado || getTextoScore(valor);

   let claseScore = "";
   if (item.mode === "funcionalidad") {{
       if (valor === 1) claseScore = "badge-modal-cumple";
       else if (valor === 0) claseScore = "badge-modal-no-cumple";
       else claseScore = "badge-modal-no-aplica";
   }} else {{
       claseScore = getClaseScore(valor);
   }}

   let puntajeTexto = item.mode === "funcionalidad" ? String(valor) : valor.toFixed(2);

   let descripcion = item.justification || "";

   return `
<div class="metric-card">
<div class="metric-card-header">
<div class="metric-card-title">${{escaparHtml(nombre)}}</div>
<div class="metric-card-score ${{claseScore}}">${{escaparHtml(estado)}}</div>
</div>

    <div class="metric-score-line">
<strong>Puntaje:</strong> ${{puntajeTexto}}
</div>

    <div class="metric-justification">
<strong>Justificación:</strong><br>

        ${{escaparHtml(descripcion)}}
</div>
</div>

`;

}}

function switchMetricTab(btn) {{
   const wrapper = btn.closest('.metric-tabs-wrapper');
   if (!wrapper) return;

   const target = btn.getAttribute('data-tab-target') || '';
   const tabs = wrapper.querySelectorAll('.metric-tab-btn');
   const panels = wrapper.querySelectorAll('.metric-tab-panel');

   tabs.forEach(function(tab) {{
       tab.classList.toggle('is-active', tab === btn);
   }});

   panels.forEach(function(panel) {{
       panel.classList.toggle('is-active', panel.getAttribute('data-tab-panel') === target);
   }});
}}

function renderDataContent(contenido) {{
   let texto = contenido;
   if (typeof texto === "object" && texto !== null) {{
       texto = JSON.stringify(texto, null, 2);
   }}
   try {{
       const parsed = JSON.parse(String(texto));
       texto = JSON.stringify(parsed, null, 2);
   }} catch (e) {{}}
   return `<div class="data-panel"><pre class="data-pre">${{escaparHtml(texto || "")}}</pre></div>`;
}}

function renderConversationContent(texto) {{
   const raw = String(texto || "").trim();
   if (!raw) {{
       return `<div class="conversation-thread"><div class="conversation-message neutral"><div class="conversation-text">Sin contenido.</div></div></div>`;
   }}
   const blocks = raw.split(/\\n\\s*\\n/).filter(Boolean);
   let messages = "";
   blocks.forEach(function(block) {{
       const match = block.match(/^\\[([^\\]]+)\\]\\s*([\\s\\S]*)$/);
       const role = match ? match[1] : "DETALLE";
       const body = match ? match[2] : block;
       const roleUpper = role.toUpperCase();
       const cssClass = roleUpper.includes("CLIENTE")
           ? "client"
           : (roleUpper.includes("AG.") || roleUpper.includes("BOT") || roleUpper.includes("PHOENIX") ? "bot" : "neutral");
       messages += `<div class="conversation-message ${{cssClass}}"><div class="conversation-role">${{escaparHtml(roleUpper)}}</div><div class="conversation-text">${{escaparHtml(body.trim())}}</div></div>`;
   }});
   return `<div class="conversation-thread">${{messages}}</div>`;
}}



function showUniqueModalFromButton(btn) {{
   let textContent = document.getElementById('uniqueModalTextContent');
   let rich = document.getElementById('uniqueModalRichContent');
   let lbl = document.getElementById('uniqueModalTitle');
   let idx = Number(btn.getAttribute('data-content-idx'));
   let tipo = btn.getAttribute('data-content-tipo');
   let titulo = btn.getAttribute('data-title') || 'Detalle';
   let contenido = '';
   lbl.textContent = titulo;
   if (
       window.__MODAL_CONTENTS__ &&
       window.__MODAL_CONTENTS__[idx] &&
       window.__MODAL_CONTENTS__[idx][tipo] !== undefined
   ) {{
       contenido = window.__MODAL_CONTENTS__[idx][tipo];
   }}
   // RESET
   textContent.style.display = "block";
   rich.style.display = "none";
   textContent.textContent = "";
   rich.innerHTML = "";
   setModalBackButtonVisible(false);

   if (tipo === "detalle_cumplimiento") {{
       textContent.style.display = "none";
       rich.style.display = "block";
       rich.innerHTML = renderDetalleCumplimiento(window.__DETALLE_CUMPLIMIENTO__);
       rich.scrollTop = 0;
       return;
   }}

   if (tipo === "conversa") {{
       textContent.style.display = "none";
       rich.style.display = "block";
       rich.innerHTML = renderConversationContent(contenido);
       rich.scrollTop = 0;
       return;
   }}

   if (tipo === "payload") {{
       textContent.style.display = "none";
       rich.style.display = "block";
       rich.innerHTML = renderDataContent(contenido);
       rich.scrollTop = 0;
       return;
   }}

   if (tipo === 'detalle_metricas') {{

   textContent.style.display = 'none';
   rich.style.display = 'block';

   let metricasFuncionales = contenido.metricas_funcionalidades || [];
   let metricas = contenido.metricas || [];
   let resumenFuncionalidades = contenido.resumen_funcionalidades || "";
   let resumenmetricas = contenido.resumen_metricas || "";

   if ((!Array.isArray(metricasFuncionales) || metricasFuncionales.length === 0) &&
       (!Array.isArray(metricas) || metricas.length === 0)) {{
       rich.innerHTML = `
<div class="metric-summary-box">
    <div class="metric-summary-title">Sin detalle de métricas</div>
    <div class="metric-summary-text">No se encontraron métricas para visualizar.</div>
</div>
`;
       return;
   }}

   let cardsFuncionales = "";
   metricasFuncionales.forEach(function(item) {{
       cardsFuncionales += renderMetricCard(item);
   }});

   let cardsMetricas = "";
   metricas.forEach(function(item) {{
       cardsMetricas += renderMetricCard(item);
   }});

   let htmlMetricas = `
<div class="metric-tabs-wrapper">
    <div class="metric-tabs">
        <button type="button" class="metric-tab-btn is-active" data-tab-target="funcionalidades" onclick="switchMetricTab(this)">Funcionalidades</button>
        <button type="button" class="metric-tab-btn" data-tab-target="metricas" onclick="switchMetricTab(this)">Métricas</button>
    </div>

    <div class="metric-tab-panel is-active" data-tab-panel="funcionalidades">
        <div class="metric-cards-grid">
            ${{cardsFuncionales}}
        </div>
        <div class="metric-summary-box">
            <div class="metric-summary-title">Resumen funcionalidades</div>
            <div class="metric-summary-text">${{escaparHtml(resumenFuncionalidades)}}</div>
        </div>
    </div>

    <div class="metric-tab-panel" data-tab-panel="metricas">
        <div class="metric-cards-grid">
            ${{cardsMetricas}}
        </div>
        <div class="metric-summary-box">
            <div class="metric-summary-title">Resumen métricas</div>
            <div class="metric-summary-text">${{escaparHtml(resumenmetricas)}}</div>
        </div>
    </div>
</div>
`;

   rich.innerHTML = htmlMetricas;
   return;
}}


   if (typeof contenido === "object" && contenido !== null) {{
       contenido = JSON.stringify(contenido, null, 2);
   }}
   textContent.textContent = contenido || '';
}}

function openGlobalModal() {{
   const modal = document.getElementById('uniqueGlobalModal');
   if (!modal) return;
   modal.classList.add('is-open');
   modal.setAttribute('aria-hidden', 'false');
   document.body.classList.add('modal-open');
}}

function closeGlobalModal() {{
   const modal = document.getElementById('uniqueGlobalModal');
   if (!modal) return;
   modal.classList.remove('is-open');
   modal.setAttribute('aria-hidden', 'true');
   document.body.classList.remove('modal-open');
   setModalBackButtonVisible(false);
}}

document.addEventListener('keydown', function(event) {{
   if (event.key === 'Escape') {{
       closeGlobalModal();
   }}
}});

document.addEventListener('DOMContentLoaded', function() {{
   const pageSize = 6;
   const table = document.getElementById('myTable');
   if (!table) return;

    const detalleCumplimientoBtn = document.querySelector('.summary-modal-btn');
   const summaryButtons = Array.from(document.querySelectorAll('.summary-switch-btn'));
   const summaryPanels = Array.from(document.querySelectorAll('[data-summary-panel]'));
    const promLabels = Array.from(document.querySelectorAll('.prom-label'));
    const promValues = Array.from(document.querySelectorAll('.prom-value'));
    const promSubs = Array.from(document.querySelectorAll('.prom-sub'));

   const rows = Array.from(table.querySelectorAll('tbody tr'));
   const filterButtons = Array.from(document.querySelectorAll('[data-result-filter]'));
   const tableInfo = document.getElementById('tableInfo');
   const pagination = document.getElementById('tablePagination');
   let activeFilter = 'TODOS';
   let currentPage = 1;
   let currentView = 'funcionalidades';

   function normalizeResult(value) {{
       const normalized = String(value || '').trim().toUpperCase();
       if (normalized === 'SUCCESS') return 'PASS';
       if (normalized === 'PASS') return 'PASS';
       if (normalized === 'FAIL') return 'FAIL';
       if (normalized === 'WARNING') return 'WARNING';
       return normalized;
   }}

   function getRowResultByView(row) {{
       const attr = currentView === 'funcionalidades' ? 'data-result-func' : 'data-result-clas';
       return normalizeResult(row.getAttribute(attr));
   }}

   function getFilteredRows() {{
       return rows.filter(function(row) {{
           if (activeFilter === 'TODOS') return true;
           return getRowResultByView(row) === activeFilter;
       }});
   }}

   function switchSummary(target) {{
       currentView = target === 'metricas' ? 'metricas' : 'funcionalidades';

       summaryButtons.forEach(function(btn) {{
           btn.classList.toggle('is-active', btn.getAttribute('data-summary-target') === currentView);
       }});

       summaryPanels.forEach(function(panel) {{
           panel.classList.toggle('is-active', panel.getAttribute('data-summary-panel') === currentView);
       }});

       promLabels.forEach(function(item) {{
           item.classList.toggle('is-active', item.getAttribute('data-prom-panel') === currentView);
       }});
       promValues.forEach(function(item) {{
           item.classList.toggle('is-active', item.getAttribute('data-prom-panel') === currentView);
       }});
       promSubs.forEach(function(item) {{
           item.classList.toggle('is-active', item.getAttribute('data-prom-panel') === currentView);
       }});

       if (detalleCumplimientoBtn) {{
           detalleCumplimientoBtn.style.display = currentView === 'funcionalidades' ? 'inline-flex' : 'none';
       }}

       table.classList.toggle('table-view-func', currentView === 'funcionalidades');
       table.classList.toggle('table-view-clas', currentView === 'metricas');

       currentPage = 1;
       renderTable();
   }}

   function createPageButton(label, page, disabled, active) {{
       const btn = document.createElement('button');
       btn.type = 'button';
       btn.className = 'table-page-btn' + (active ? ' is-active' : '');
       btn.textContent = label;
       btn.disabled = disabled;
       btn.addEventListener('click', function() {{
           currentPage = page;
           renderTable();
       }});
       return btn;
   }}

   function renderPagination(totalPages) {{
       if (!pagination) return;
       pagination.innerHTML = '';
       pagination.appendChild(createPageButton('Anterior', Math.max(1, currentPage - 1), currentPage === 1, false));
       for (let page = 1; page <= totalPages; page++) {{
           pagination.appendChild(createPageButton(String(page), page, false, page === currentPage));
       }}
       pagination.appendChild(createPageButton('Siguiente', Math.min(totalPages, currentPage + 1), currentPage === totalPages, false));
   }}

   function renderTable() {{
       const filteredRows = getFilteredRows();
       const total = filteredRows.length;
       const totalPages = Math.max(1, Math.ceil(total / pageSize));
       if (currentPage > totalPages) currentPage = totalPages;

       const startIndex = (currentPage - 1) * pageSize;
       const endIndex = Math.min(startIndex + pageSize, total);
       rows.forEach(function(row) {{
           row.style.display = 'none';
       }});
       filteredRows.slice(startIndex, endIndex).forEach(function(row) {{
           row.style.display = '';
       }});

       const visibleRows = total === 0 ? 0 : endIndex - startIndex;
       if (tableInfo) {{
           tableInfo.textContent = 'Mostrando ' + visibleRows + ' de ' + total;
       }}
       renderPagination(totalPages);
   }}

   filterButtons.forEach(function(btn) {{
       btn.addEventListener('click', function() {{
           const rawFilter = btn.getAttribute('data-result-filter') || 'TODOS';
           activeFilter = normalizeResult(rawFilter);
           currentPage = 1;
           filterButtons.forEach(function(item) {{
               item.classList.remove('active');
           }});
           btn.classList.add('active');
           renderTable();
       }});
   }});

   summaryButtons.forEach(function(btn) {{
       btn.addEventListener('click', function() {{
           switchSummary(btn.getAttribute('data-summary-target') || 'funcionalidades');
       }});
   }});

   switchSummary('funcionalidades');
}});

</script>
</body>
</html>
"""

date_str = datetime.now().strftime("%d%m%Y_%H%M%S")
report_name = f"Rep-paralelizado-{date_str}.html"
report_path = os.path.join(OUTPUT_DIR, report_name)
with open(report_path, "w", encoding="utf-8") as f:
    f.write(html_doc)
print("Reporte HTML generado:", report_path)
csv_name = report_name.replace(".html", ".csv")
csv_path = os.path.join(OUTPUT_DIR, csv_name)
df.to_csv(csv_path, index=False, sep=";", encoding="utf-8-sig")
print("CSV generado:", csv_path)

print("\n[RESUMEN FINAL] id_test | chat_id")
for resultado in rows:
    print(
        f"- {safe_str(resultado.get('id_test'))} | "
        f"{format_chat_id_log(resultado.get('chat_id'))}"
    )

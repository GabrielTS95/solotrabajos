import os
import json
import html
import requests
import pandas as pd
from datetime import datetime
from openai import AzureOpenAI
import httpx
from faker import Faker
from datetime import timedelta

http_client = httpx.Client(verify=False)  # <--- Desactiva SSL

# ======================================================================================================================
# CONFIGURACIÓN LOCAL
# ======================================================================================================================
AZURE_OPENAI_API_KEY = os.getenv(
    "AZURE_OPENAI_API_KEY",
    "",
)
AZURE_OPENAI_ENDPOINT = os.getenv(
    "AZURE_OPENAI_ENDPOINT",
    "",
)
AZURE_OPENAI_API_VERSION = os.getenv(
    "AZURE_OPENAI_API_VERSION",
    "",
)
# En Azure OpenAI, model=deployment name
MODEL_NAME = "gpt-4.1"
API_KEY = os.getenv("BOT_API_KEY", "")
MAX_TURNS_SAFE = 15
URL_CHAT = ""
# Ruta local

# CSV_PATH = r"D:\Datos de Usuarios\T76960\Squad Phoenix\auto-phoenix\escenarios_funcionalidades.csv"
CSV_PATH = os.getenv(
    "CSV_PATH",
    r"D:\Datos de Usuarios\T76960\Squad Phoenix\auto-phoenix\escenarios_funcionalidades_especificas_michael.csv",
)
# CSV_PATH = (r"D:\Datos de Usuarios\T76960\Squad Phoenix\auto-phoenix\escenarios_martin_2.csv")
# CSV_PATH = r"D:\Datos de Usuarios\T76960\Squad Phoenix\auto-phoenix\escenarios_complementarias.csv"

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

def obtener_cliente_azure():
    return client


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
- Evasivo/a: “luego”, “no puedo hablar”, “ya veré”.
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


def normalizar_score(x):
    try:
        v = float(x)
        if v < 0:
            return 0.0
        if v > 1:
            return 1.0
        return round(v, 2)
    except Exception:
        return 0.0


def clasificar_cumplimiento(score):
    score = normalizar_score(score)
    if score <= 0.35:
        return {
            "estado": "NO CUMPLE",
            "resultado": "FAIL",
            "css": "fail",
            "badge": "badge-fail",
            "fill": "fill-fail",
        }
    if score <= 0.80:
        return {
            "estado": "PARCIALMENTE",
            "resultado": "WARNING",
            "css": "warning",
            "badge": "badge-warning",
            "fill": "fill-warning",
        }
    return {
        "estado": "CUMPLE",
        "resultado": "PASS",
        "css": "pass",
        "badge": "badge-pass",
        "fill": "fill-pass",
    }


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


def formatear_fecha_juez(fecha):
    return (
        f"{DIAS_SEMANA_ES[fecha.weekday()]} {fecha.day:02d} "
        f"de {MESES_ES[fecha.month - 1]} de {fecha.year} "
        f"({fecha.strftime('%Y-%m-%d')})"
    )


def construir_contexto_fecha_base_juez():
    fecha_base = datetime.now()
    manana = fecha_base + timedelta(days=1)
    pasado_manana = fecha_base + timedelta(days=2)
    dias_hasta_proximo_lunes = (7 - fecha_base.weekday()) % 7 or 7
    proximo_lunes = fecha_base + timedelta(days=dias_hasta_proximo_lunes)
    proximo_domingo = proximo_lunes + timedelta(days=6)

    return (
        f"Fecha base actual: {formatear_fecha_juez(fecha_base)}.\n"
        f'Equivalencia obligatoria: "mañana" = {formatear_fecha_juez(manana)}.\n'
        f'Equivalencia obligatoria: "pasado mañana" = {formatear_fecha_juez(pasado_manana)}.\n'
        f'Equivalencia obligatoria: "la próxima semana" = del {formatear_fecha_juez(proximo_lunes)} '
        f"al {formatear_fecha_juez(proximo_domingo)}."
    )


def llm_judge_metricas(
        question: str, caso_de_prueba: str = "", reglas_juez: str = "", model=MODEL_NAME
):
    contexto_fecha_base = construir_contexto_fecha_base_juez()
    prompt = f"""
Eres un evaluador experto en pruebas de negocio de cobranzas digitales.
Debes evaluar la siguiente conversación entre el AGENTE (BOT) y el CLIENTE.
Debes centrarte EXCLUSIVAMENTE en lo que se indica en 'REGLAS DEL JUEZ' y en el 'CASO DE PRUEBA'.
CASO DE PRUEBA:
{caso_de_prueba or 'Sin caso de prueba definido.'}
REGLAS DEL JUEZ:
{reglas_juez or 'Sin reglas para este caso.'}
FECHA BASE PARA EVALUAR FECHAS RELATIVAS:
{contexto_fecha_base}
Debes evaluar con estas métricas:
- coherencia
- fluidez
- cumplimiento
- integridad
- claridad
- correccion
Definiciones:
- coherencia: Evalúa el grado en que las respuestas del agente mantienen una lógica interna y se alinean con el contexto específico del caso, así como con las reglas definidas para la conversación. La conversación debe tener un hilo argumental consistente y responder de manera esperada ante diferentes situaciones o estímulos del usuario. La coherencia implica que no existan contradicciones, rupturas temáticas ni desviaciones aleatorias respecto al propósito de persuadir al cliente deudor.
- fluidez: Mide cuán natural, fácil de seguir y conectadas son las intervenciones del agente. La fluidez implica que el lenguaje empleado es propio de hablantes nativos o avanzados, evitando trabas, frases forzadas o uso inadecuado de conectores. Un agente fluido se comunica de forma orgánica, sin pausas abruptas o construcciones gramaticales extrañas, permitiendo una experiencia conversacional agradable y realista.
- cumplimiento: Se refiere al grado en que el agente cumple y satisface los objetivos y requerimientos planteados explícitamente en el CASO DE PRUEBA. El cumplimiento implica que el agente realiza o verifica todas las acciones que se espera (por ejemplo: propuesta de pago, envío de recordatorio, entrega de argumentos persuasivos), atendiendo los criterios definidos como éxito para la situación planteada.
- integridad: Evalúa si la conversación cubre todos los aspectos necesarios del caso, sin omitir información o pasos clave que podrían afectar el resultado. Un agente íntegro no deja cabos sueltos ni vacíos significativos en la gestión del caso deudor: aborda todos los puntos relevantes y anticipa posibles preguntas o resistencias, proporcionando soluciones o respuestas completas.
- claridad: Mide la facilidad con la que el interlocutor puede entender el mensaje del agente. Un mensaje claro es directo, específico y no genera ambigüedad o malentendidos; el usuario entiende exactamente lo que se le está proponiendo o solicitando. Se valoran expresiones concisas y la ausencia de tecnicismos innecesarios, redundancias o frases vagas.
- correccion: Evalúa la calidad lingüística y gramatical de los enunciados del agente. Implica un uso apropiado de ortografía, gramática, sintaxis y puntuación, así como la ausencia de errores que puedan dificultar la comprensión o afectar la imagen profesional del agente. Además, contempla la adecuación del registro del idioma al contexto y al perfil del cliente.
Reglas obligatorias:
- Para la métrica CUMPLIMIENTO debes evaluar principalmente si el agente logró o no lo que se pide validar en el CASO DE PRUEBA
- Si el agente contradice, omite o no alcanza el objetivo del CASO DE PRUEBA, el puntaje de cumplimiento debe bajar
- Si el CASO DE PRUEBA valida interpretación de fechas relativas, debes evaluar estrictamente expresiones como "mañana", "pasado mañana", "la próxima semana", "este lunes" o "el próximo martes" usando la FECHA BASE indicada arriba.
- En casos de fechas relativas, antes de puntuar debes comparar: fecha relativa del cliente, fecha absoluta correcta, fecha asumida por el agente y si coinciden.
- Si el agente convierte mal una fecha relativa, cumplimiento debe ser <= 0.40.
- Si el agente contradice la fecha relativa del cliente, coherencia debe ser <= 0.60.
- Si el agente no valida una fecha ambigua o una fecha que no está dentro de las opciones disponibles, integridad debe ser <= 0.70.
- Si el mensaje puede confundir al cliente sobre la fecha real de la cita, claridad debe ser <= 0.70.
- Si la fecha relativa solicitada por el cliente no está dentro de las opciones disponibles ofrecidas por el agente, el agente debe aclararlo y ofrecer nuevamente fechas válidas; no debe transformarla en una fecha disponible distinta sin confirmación.
- Fluidez no debe compensar un error funcional de interpretación de fecha.
- Correccion solo evalúa gramática, ortografía y redacción; no debe ocultar errores funcionales.
- Cada métrica debe estar entre 0.00 y 1.00
- score_total debe ser igual al puntaje de cumplimiento
- Las métricas coherencia, fluidez, integridad, claridad y correccion no se promedian para el resultado final
- resultado = "FAIL" si cumplimiento está entre 0.00 y 0.35
- resultado = "WARNING" si cumplimiento está entre 0.36 y 0.80
- resultado = "PASS" si cumplimiento está entre 0.81 y 1.00
- Para cada criterio debes dar una explicación breve y puntual
- Devuelve SOLO JSON válido
- No agregues texto fuera del JSON
Formato de salida esperado:
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
    t0 = datetime.now()
    response = obtener_cliente_azure().chat.completions.create(
        model=model,
        messages=[
            {
                "role": "system",
                "content": "Responde únicamente con JSON válido y sin markdown.",
            },
            {"role": "user", "content": prompt},
        ],
        max_tokens=700,
        temperature=0,
    )
    latency_s = round((datetime.now() - t0).total_seconds(), 2)
    content = (response.choices[0].message.content or "").strip()
    try:
        start = content.find("{")
        end = content.rfind("}")
        parsed = json.loads(content[start : end + 1])

        def sf(x):
            try:
                v = float(x)
                if v < 0:
                    return 0.0
                if v > 1:
                    return 1.0
                return round(v, 2)
            except Exception:
                return 0.0

        m_coherencia = sf(parsed.get("coherencia", 0))
        m_fluidez = sf(parsed.get("fluidez", 0))
        m_cumplimiento = sf(parsed.get("cumplimiento", 0))
        m_integridad = sf(parsed.get("integridad", 0))
        m_claridad = sf(parsed.get("claridad", 0))
        m_correccion = sf(parsed.get("correccion", 0))
        score_total = m_cumplimiento
        resultado = clasificar_cumplimiento(m_cumplimiento)["resultado"]
        result = {
            "m_coherencia": m_coherencia,
            "exp_coherencia": str(parsed.get("exp_coherencia", "")),
            "m_fluidez": m_fluidez,
            "exp_fluidez": str(parsed.get("exp_fluidez", "")),
            "m_cumplimiento": m_cumplimiento,
            "exp_cumplimiento": str(parsed.get("exp_cumplimiento", "")),
            "m_integridad": m_integridad,
            "exp_integridad": str(parsed.get("exp_integridad", "")),
            "m_claridad": m_claridad,
            "exp_claridad": str(parsed.get("exp_claridad", "")),
            "m_correccion": m_correccion,
            "exp_correccion": str(parsed.get("exp_correccion", "")),
            "score_total": score_total,
            "resultado": resultado,
            "justificacion": str(parsed.get("justificacion", "")),
            "raw_json": json.dumps(parsed, ensure_ascii=False, indent=2),
            "latencia_eval_s": latency_s,
        }
        return result
    except Exception as e:
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
            "justificacion": f"Error analizando salida del juez: {e}",
            "raw_json": content,
            "latencia_eval_s": latency_s,
        }


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
        timeout=60,
        verify=False,
    )
    print(r1.json)
    r1.raise_for_status()
    resp_create = r1.json()
    chat_id = resp_create.get("chat", {}).get("id")
    token = resp_create.get("token")
    user_id = resp_create.get("chat", {}).get("user_id")
    if not chat_id or not token:
        raise RuntimeError(f"No se obtuvo chat_id/token. Resp: {resp_create}")
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


def add_new_cic_to_customer_proc(request_cliente_json):
    print("INSERSANTO NUEVOS REGISTROS EN DH_CUSTOMER_PROC")
    # payload_create = {"user_id": user_id, "initial_message": mensaje_inicio}
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
    url = "https://fncteu2ainac02.azurewebsites.net/api/setcicinputs"

    response = requests.post(
        url,
        json=correct_payload,
        headers=headers_create,
        timeout=60,
        verify=False,
    )

    # print("Payload sent:", correct_payload)
    print("Status code:", response.status_code)
    print("Response body:", response.text)


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

    # -----------------------
    # NUEVOS CAMPOS
    # -----------------------

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

    # -----------------------
    # FIN NUEVOS CAMPOS
    # -----------------------

    # Deuda soles     deuda_soles_csv = saf... de Erwin Torres
    # Erwin Torres

    # Deuda soles
    deuda_soles_csv = safe_str(user_row.get("deuda_soles"))
    val_debt_amount_1 = (
        float(deuda_soles_csv)
        if deuda_soles_csv
        else round(fake.pyfloat(right_digits=2, min_value=500, max_value=15000), 2)
    )
    val_currency1 = "Soles"

    # Cuenta 1
    accnum1 = fake.bothify(text="016################", letters="")

    # Deuda dólares
    deuda_dolares_csv = safe_str(user_row.get("deuda_dolares"))
    val_debt_amount_2 = float(deuda_dolares_csv) if deuda_dolares_csv else 0.0
    val_currency2 = ""
    accnum2 = ""

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
        url_msg, json=payload_msg, headers=headers_msg, timeout=60, verify=False
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


def construir_evaluacion_error(motivo):
    return {
        "m_coherencia": 0.0,
        "exp_coherencia": "Error en evaluacion.",
        "m_fluidez": 0.0,
        "exp_fluidez": "Error en evaluacion.",
        "m_cumplimiento": 0.0,
        "exp_cumplimiento": "Error en evaluacion.",
        "m_integridad": 0.0,
        "exp_integridad": "Error en evaluacion.",
        "m_claridad": 0.0,
        "exp_claridad": "Error en evaluacion.",
        "m_correccion": 0.0,
        "exp_correccion": "Error en evaluacion.",
        "score_total": 0.0,
        "resultado": "FAIL",
        "justificacion": motivo,
        "raw_json": "{}",
        "latencia_eval_s": 0.0,
    }


def construir_row_resultado(
        orden_csv,
        user,
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
        scenario_exec_time,
):
    return {
        "_orden_csv": orden_csv,
        "_scenario_seconds": scenario_exec_time.total_seconds(),
        "id_test": safe_str(user.get("id_test")),
        "caso_de_prueba": caso_de_prueba,
        "tipo_cliente": tipo_cliente,
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
        "m_coherencia": eval_juez["m_coherencia"],
        "exp_coherencia": eval_juez["exp_coherencia"],
        "m_fluidez": eval_juez["m_fluidez"],
        "exp_fluidez": eval_juez["exp_fluidez"],
        "m_cumplimiento": eval_juez["m_cumplimiento"],
        "exp_cumplimiento": eval_juez["exp_cumplimiento"],
        "m_integridad": eval_juez["m_integridad"],
        "exp_integridad": eval_juez["exp_integridad"],
        "m_claridad": eval_juez["m_claridad"],
        "exp_claridad": eval_juez["exp_claridad"],
        "m_correccion": eval_juez["m_correccion"],
        "exp_correccion": eval_juez["exp_correccion"],
        "score_total": eval_juez["score_total"],
        "json_juez": eval_juez["raw_json"],
        "latencia_eval_s": eval_juez["latencia_eval_s"],
        "payload": json.dumps(request_cliente_json, ensure_ascii=False, indent=2),
        "tiempo_ejecucion": format_td_hms(scenario_exec_time),
        "secuencia_mensaje": "\n".join(secuencia_mensaje),
    }


def ejecutar_escenario(orden_csv, user):
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
    conversa = []
    status = "OK"
    bot_turns = 0
    last_bot = ""
    total_bot_latency_s = 0.0
    total_sim_latency_s = 0.0
    full_conversation = ""

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
        bot_text, bot_lat, exit_status, data = send_bot_message(
            url_msg, headers_msg, mensaje_inicio
        )
        total_bot_latency_s += bot_lat
        bot_turns += 1
        last_bot = bot_text
        conversa.append(("bot", bot_text))

        for mensaje_secuencia in secuencia_mensaje:
            if exit_status == 1:
                status = "BOT indico fin de conversacion durante secuencia definida"
                break

            mensaje_secuencia = safe_str(mensaje_secuencia).strip()
            if not mensaje_secuencia:
                continue

            print(f"[{id_test}] MENSAJE SECUENCIA => {repr(mensaje_secuencia)}")
            conversa.append(("usuario", mensaje_secuencia))
            bot_text, bot_lat, exit_status, data = send_bot_message(
                url_msg, headers_msg, mensaje_secuencia
            )
            total_bot_latency_s += bot_lat
            bot_turns += 1
            last_bot = bot_text
            conversa.append(("bot", bot_text))

        turn_count = 0
        while True:
            if exit_status == 1:
                status = "BOT indico fin de conversacion"
                break
            if turn_count >= MAX_TURNS_SAFE:
                status = "CORTADO: Exceso de turnos"
                break

            t0 = datetime.now()
            sim_text = llamada_user_simulator(prompt_cliente, conversa)
            sim_lat = round((datetime.now() - t0).total_seconds(), 2)
            total_sim_latency_s += sim_lat
            turn_count += 1

            print(
                f"[{id_test} | {nombre_completo} | {tipo_cliente}] "
                f"CLIENTE => {repr(sim_text)}"
            )

            if not sim_text:
                status = "ERROR: USER-SIMULATOR devolvio vacio"
                break
            if sim_text.strip().lower() in ["fin", "adios", "adiós"]:
                status = "OK (simulador termino)"
                break

            conversa.append(("usuario", sim_text))
            bot_text, bot_lat, exit_status, data = send_bot_message(
                url_msg, headers_msg, sim_text
            )
            total_bot_latency_s += bot_lat
            bot_turns += 1
            last_bot = bot_text
            conversa.append(("bot", bot_text))

    except Exception as e:
        status = f"ERROR {type(e).__name__}: {e}"
    finally:
        scenario_exec_time = datetime.now() - scenario_start
        full_conversation = build_full_conversation(conversa)

    try:
        if full_conversation:
            eval_juez = llm_judge_metricas(
                question=full_conversation,
                caso_de_prueba=caso_de_prueba,
                reglas_juez=reglas_juez,
            )
        else:
            eval_juez = construir_evaluacion_error(
                "No se genero conversacion para evaluar."
            )
    except Exception as e:
        eval_juez = construir_evaluacion_error(
            f"Excepcion ejecutando juez: {type(e).__name__}: {e}"
        )

    print(f"[FIN] Escenario {orden_csv + 1}: {id_test} - {eval_juez['resultado']}")
    return construir_row_resultado(
        orden_csv,
        user,
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
        scenario_exec_time,
    )


def ejecutar_escenarios_secuencial(df_escenarios):
    total_escenarios = len(df_escenarios)
    if total_escenarios == 0:
        return [], timedelta(0)

    print(f"[INFO] Ejecutando {total_escenarios} escenarios en modo secuencial.")

    inicio_ejecucion = datetime.now()
    rows_resultado = []
    for orden_csv, (_, user) in enumerate(df_escenarios.iterrows()):
        completados = orden_csv + 1
        user = user.copy()
        try:
            rows_resultado.append(ejecutar_escenario(orden_csv, user))
        except Exception as e:
            eval_juez = construir_evaluacion_error(
                f"Excepcion inesperada ejecutando escenario: {type(e).__name__}: {e}"
            )
            rows_resultado.append(
                construir_row_resultado(
                    orden_csv,
                    user,
                    {},
                    safe_str(user.get("tipo_cliente")),
                    safe_str(user.get("caso_de_prueba")),
                    safe_str(user.get("mensaje_inicio")),
                    parsear_secuencia_mensajes(user.get("secuencia_mensaje")),
                    safe_str(user.get("cic")),
                    safe_str(user.get("dni")),
                    safe_str(user.get("Cel")),
                    (
                            safe_str(user.get("nombre"))
                            + " "
                            + safe_str(user.get("apellidos"))
                    ).strip(),
                    safe_str(user.get("deuda_soles")),
                    safe_str(user.get("deuda_dolares")),
                    safe_str(user.get("tipo_deuda")),
                    f"ERROR {type(e).__name__}: {e}",
                    0,
                    0.0,
                    0.0,
                    "",
                    safe_str(user.get("reglas_negocio_cliente")),
                    safe_str(user.get("reglas_negocio_juez")),
                    [],
                    eval_juez,
                    timedelta(0),
                )
            )
        print(f"[PROGRESO] {completados}/{total_escenarios} escenarios completados")

    rows_resultado.sort(key=lambda row: row.get("_orden_csv", 0))
    for row in rows_resultado:
        row.pop("_scenario_seconds", None)

    for row in rows_resultado:
        row.pop("_orden_csv", None)

    return rows_resultado, datetime.now() - inicio_ejecucion


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
df_users = df_users.iloc[0:0]
# ======================================================================================================================
# PROCESO PRINCIPAL
# ======================================================================================================================
rows = []
for _, user in df_users.iterrows():
    scenario_start = datetime.now()  # INICIO del escenario
    id_test = safe_str(user.get("id_test"))
    request_cliente_json = generar_payload(user)
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
    datos_prompt = obtener_datos_prompt_desde_payload(request_cliente_json)
    nombre_completo = datos_prompt.get("nombre_completo") or nombre_completo
    deuda_soles = datos_prompt.get("deuda_soles") or deuda_soles
    deuda_dolares = datos_prompt.get("deuda_dolares") or deuda_dolares
    cic = datos_prompt.get("cic") or cic
    dni = datos_prompt.get("dni") or dni
    cel = datos_prompt.get("cel") or cel
    tipo_deuda = datos_prompt.get("tipo_deuda") or tipo_deuda
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
    conversa = []
    status = "OK"
    bot_turns = 0
    last_bot = ""
    total_bot_latency_s = 0.0
    total_sim_latency_s = 0.0
    ultimate_response = {}

    try:
        print("-----------------------start")
        add_new_cic_to_customer_proc(request_cliente_json)
        print("-----------------------end")
        chat_id, url_msg, headers_msg = create_chat_and_headers(request_cliente_json)
        # MENSAJE INICIAL
        conversa.append(("usuario", mensaje_inicio))
        bot_text, bot_lat, exit_status, data = send_bot_message(
            url_msg, headers_msg, mensaje_inicio
        )
        total_bot_latency_s += bot_lat
        bot_turns += 1
        last_bot = bot_text
        conversa.append(("bot", bot_text))
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
            bot_text, bot_lat, exit_status, data = send_bot_message(
                url_msg, headers_msg, mensaje_secuencia
            )
            total_bot_latency_s += bot_lat
            bot_turns += 1
            last_bot = bot_text
            conversa.append(("bot", bot_text))
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
            bot_text, bot_lat, exit_status, data = send_bot_message(
                url_msg, headers_msg, sim_text
            )
            total_bot_latency_s += bot_lat
            bot_turns += 1
            last_bot = bot_text
            conversa.append(("bot", bot_text))

    except Exception as e:
        status = f"ERROR {type(e).__name__}: {e}"
    finally:
        scenario_end = datetime.now()
        scenario_exec_time = scenario_end - scenario_start
        total_exec_time += scenario_exec_time
        full_conversation = build_full_conversation(conversa)

    try:
        eval_juez = llm_judge_metricas(
            question=full_conversation,
            caso_de_prueba=caso_de_prueba,
            reglas_juez=reglas_juez,
        )

    except Exception as e:
        eval_juez = {
            "m_coherencia": 0.0,
            "exp_coherencia": "Error en evaluación.",
            "m_fluidez": 0.0,
            "exp_fluidez": "Error en evaluación.",
            "m_cumplimiento": 0.0,
            "exp_cumplimiento": "Error en evaluación.",
            "m_integridad": 0.0,
            "exp_integridad": "Error en evaluación.",
            "m_claridad": 0.0,
            "exp_claridad": "Error en evaluación.",
            "m_correccion": 0.0,
            "exp_correccion": "Error en evaluación.",
            "score_total": 0.0,
            "resultado": "FAIL",
            "justificacion": f"Excepción: {type(e).__name__}: {e}",
            "raw_json": "{}",
            "latencia_eval_s": 0.0,
        }

    rows.append(
        {
            "id_test": id_test,
            "caso_de_prueba": caso_de_prueba,
            "tipo_cliente": tipo_cliente,
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
            "m_coherencia": eval_juez["m_coherencia"],
            "exp_coherencia": eval_juez["exp_coherencia"],
            "m_fluidez": eval_juez["m_fluidez"],
            "exp_fluidez": eval_juez["exp_fluidez"],
            "m_cumplimiento": eval_juez["m_cumplimiento"],
            "exp_cumplimiento": eval_juez["exp_cumplimiento"],
            "m_integridad": eval_juez["m_integridad"],
            "exp_integridad": eval_juez["exp_integridad"],
            "m_claridad": eval_juez["m_claridad"],
            "exp_claridad": eval_juez["exp_claridad"],
            "m_correccion": eval_juez["m_correccion"],
            "exp_correccion": eval_juez["exp_correccion"],
            "score_total": eval_juez["score_total"],
            "json_juez": eval_juez["raw_json"],
            "latencia_eval_s": eval_juez["latencia_eval_s"],
            # "url_msg": url_msg,  # Guarda la última o más reciente
            "payload": json.dumps(request_cliente_json, ensure_ascii=False, indent=2),
            "tiempo_ejecucion": format_td_hms(scenario_exec_time),
            "secuencia_mensaje": "\n".join(secuencia_mensaje),
        }
    )
rows, total_exec_time = ejecutar_escenarios_secuencial(df_users_ejecutar)
total_exec_time_formatted = format_td_hms(total_exec_time)
df = pd.DataFrame(rows)
print(df.head())


# Contadores escenarios PASS y FAIL y su porcentaje sobre el total
total_cases = len(df)
total_pass = df["status_prueba"].astype(str).str.upper().eq("PASS").sum()
total_warning = df["status_prueba"].astype(str).str.upper().eq("WARNING").sum()
total_fail = df["status_prueba"].astype(str).str.upper().eq("FAIL").sum()
pass_percent = round((total_pass / total_cases) * 100) if total_cases else 0
warning_percent = round((total_warning / total_cases) * 100) if total_cases else 0
fail_percent = round((total_fail / total_cases) * 100) if total_cases else 0
pass_warning_percent = min(100, pass_percent + warning_percent)


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
    elif status == "WARNING":
        return "<span class='badge-warning'>WARNING</span>"
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
    "Tiempo Ejecucion",
    "Resultado",
    "Acciones",
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


def metric_score_html(value):
    score = normalizar_score(value)
    css_class = "metric-score-good" if score >= 0.80 else "metric-score-bad"
    return f'<span class="metric-score {css_class}">{score:.2f}</span>'


def cumplimiento_score_html(value):
    score = normalizar_score(value)
    info = clasificar_cumplimiento(score)
    return f'<span class="metric-score metric-score-{info["css"]}">{score:.2f}</span>'


def puntuacion_cumplimiento_html(value):
    score = normalizar_score(value)
    info = clasificar_cumplimiento(score)
    score_pct = max(0, min(100, round(score * 100)))
    return f"""
<div class="score-wrap score-status-wrap">
<span class="score-status score-status-{info["css"]}">{info["estado"]}</span>
<div class="score-bar">
<div class="score-fill {info["fill"]}" style="width:{score_pct}%"></div>
</div>
</div>
   """


html_tablerows = []
modal_contents = []
for i, (_, r) in enumerate(df.iterrows()):
    fila_modal = {
        "payload": str(r.get("payload", "")),
        "conversa": "",
        "detalle_metricas": {
            "cumplimiento": [r.get("m_cumplimiento", 0), r.get("exp_cumplimiento", "")],
            "coherencia": [r.get("m_coherencia", 0), r.get("exp_coherencia", "")],
            "fluidez": [r.get("m_fluidez", 0), r.get("exp_fluidez", "")],
            "integridad": [r.get("m_integridad", 0), r.get("exp_integridad", "")],
            "claridad": [r.get("m_claridad", 0), r.get("exp_claridad", "")],
            "correccion": [r.get("m_correccion", 0), r.get("exp_correccion", "")],
            "justificacion": r.get("comentario_status_prueba", ""),
        },
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
    score = normalizar_score(r.get("m_cumplimiento", r.get("score_total", 0)))
    cumplimiento_info = clasificar_cumplimiento(score)
    status = cumplimiento_info["resultado"]
    badge = f"<span class='{cumplimiento_info['badge']}'>{status}</span>"
    puntuacion_html = puntuacion_cumplimiento_html(score)
    row_html = f"""
<tr data-result="{status}">
<td data-label="Cod. Test">{escape_cell(r.get("id_test"))}</td>
<td data-label="Escenario" class="td-ellipsis" title="{escape_cell(r.get('caso_de_prueba'))}">
           {html.escape(resumir_texto(r.get("caso_de_prueba"), 42))}
</td>
<td data-label="Cumplimiento">{cumplimiento_score_html(score)}</td>
<td data-label="Coherencia">{metric_score_html(r.get("m_coherencia", 0))}</td>
<td data-label="Fluidez">{metric_score_html(r.get("m_fluidez", 0))}</td>
<td data-label="Integridad">{metric_score_html(r.get("m_integridad", 0))}</td>
<td data-label="Claridad">{metric_score_html(r.get("m_claridad", 0))}</td>
<td data-label="Correccion">{metric_score_html(r.get("m_correccion", 0))}</td>
<td data-label="Puntuacion">{puntuacion_html}</td>
<td data-label="Tiempo Ejecucion" class="td-exec-time">{escape_cell(r.get("tiempo_ejecucion"))}</td>
<td data-label="Resultado">{badge}</td>
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


def construir_detalle_cumplimiento_html():
    resumen = f"""
<table class="compliance-summary-table">
<thead>
<tr>
<th colspan="2" class="summary-fail">NO CUMPLE</th>
<th colspan="2" class="summary-warning">PARCIALMENTE</th>
<th colspan="2" class="summary-pass">SI CUMPLE</th>
<th rowspan="2">Total</th>
</tr>
<tr>
<th>CANT</th><th>%</th>
<th>CANT</th><th>%</th>
<th>CANT</th><th>%</th>
</tr>
</thead>
<tbody>
<tr>
<td><button type="button" class="compliance-count-btn compliance-count-fail" onclick="showCumplimientoStatusModal('FAIL')">{total_fail}</button></td><td>{fail_percent}%</td>
<td><button type="button" class="compliance-count-btn compliance-count-warning" onclick="showCumplimientoStatusModal('WARNING')">{total_warning}</button></td><td>{warning_percent}%</td>
<td><button type="button" class="compliance-count-btn compliance-count-pass" onclick="showCumplimientoStatusModal('PASS')">{total_pass}</button></td><td>{pass_percent}%</td>
<td>{total_cases}</td>
</tr>
</tbody>
</table>
   """

    return f"""
<div class="compliance-detail-report">
<div class="compliance-report-title">DETALLE CUMPLIMIENTO</div>
{resumen}
</div>
   """


detalle_cumplimiento_html = construir_detalle_cumplimiento_html()


def construir_escenarios_cumplimiento_html(resultado, titulo, css, cantidad):
    filas = []
    for _, r in df.iterrows():
        score = normalizar_score(r.get("m_cumplimiento", r.get("score_total", 0)))
        if clasificar_cumplimiento(score)["resultado"] != resultado:
            continue
        escenario = safe_str(r.get("caso_de_prueba"))
        detalle = safe_str(r.get("exp_cumplimiento"))
        filas.append(
            f"""
<tr class="compliance-row compliance-{css}">
<td>{escape_cell(r.get("id_test"))}</td>
<td class="compliance-text-cell" title="{escape_cell(escenario)}">{html.escape(resumir_texto(escenario, 110))}</td>
<td class="compliance-text-cell" title="{escape_cell(detalle)}">{html.escape(resumir_texto(detalle, 150))}</td>
<td class="compliance-score-cell">{cumplimiento_score_html(score)}</td>
</tr>
           """
        )

    if not filas:
        filas.append(
            f'<tr><td colspan="4" class="compliance-empty">Sin escenarios en {titulo}.</td></tr>'
        )

    titulo_display = {
        "NO CUMPLE": "No Cumple",
        "PARCIALMENTE": "Parcialmente",
        "SI CUMPLE": "Si Cumple",
    }.get(titulo, titulo)

    return f"""
<div class="compliance-scenarios-report">
<div class="compliance-scenarios-count">{titulo_display}: {cantidad} escenario(s)</div>
<div class="compliance-table-wrap">
<table class="compliance-detail-table compliance-scenarios-table">
<thead>
<tr>
<th>COD. TEST</th>
<th>ESCENARIO</th>
<th>DETALLE DE LA METRICA</th>
<th>Score</th>
</tr>
</thead>
<tbody>
{''.join(filas)}
</tbody>
</table>
</div>
</div>
   """


detalle_cumplimiento_por_estado = {
    "FAIL": {
        "titulo": "Escenarios Por Cumplimiento: No Cumple",
        "html": construir_escenarios_cumplimiento_html("FAIL", "NO CUMPLE", "fail", total_fail),
    },
    "WARNING": {
        "titulo": "Escenarios Por Cumplimiento: Parcialmente",
        "html": construir_escenarios_cumplimiento_html("WARNING", "PARCIALMENTE", "warning", total_warning),
    },
    "PASS": {
        "titulo": "Escenarios Por Cumplimiento: Si Cumple",
        "html": construir_escenarios_cumplimiento_html("PASS", "SI CUMPLE", "pass", total_pass),
    },
}

html_modal_contents = (
        "<script>\nwindow.__MODAL_CONTENTS__ = "
        + json.dumps(modal_contents, ensure_ascii=False)
        + ";\nwindow.__CUMPLIMIENTO_DETAIL__ = "
        + json.dumps(detalle_cumplimiento_html, ensure_ascii=False)
        + ";\nwindow.__CUMPLIMIENTO_GROUP_DETAILS__ = "
        + json.dumps(detalle_cumplimiento_por_estado, ensure_ascii=False)
        + ";\n</script>"
)

html_table = f"""
<div class="table-card">
<div class="table-card-header">
<div class="table-title">Resultados por Escenario</div>
<div class="result-filter" aria-label="Filtrar por resultado">
<button type="button" class="filter-btn filter-icon-btn active" data-result-filter="TODOS" title="TODOS" aria-label="TODOS">
<svg viewBox="0 0 24 24" width="17" height="17" fill="none" stroke="currentColor" stroke-width="2"><path d="M4 6h16M4 12h16M4 18h16"></path></svg>
</button>
<button type="button" class="filter-btn filter-icon-btn" data-result-filter="PASS" title="PASS" aria-label="PASS">
<svg viewBox="0 0 24 24" width="17" height="17" fill="none" stroke="currentColor" stroke-width="2"><path d="M20 6 9 17l-5-5"></path></svg>
</button>
<button type="button" class="filter-btn filter-icon-btn" data-result-filter="WARNING" title="WARNING" aria-label="WARNING">
<svg viewBox="0 0 24 24" width="17" height="17" fill="none" stroke="currentColor" stroke-width="2"><path d="M10.3 3.9 1.8 18a2 2 0 0 0 1.7 3h17a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0Z"></path><path d="M12 9v4"></path><path d="M12 17h.01"></path></svg>
</button>
<button type="button" class="filter-btn filter-icon-btn" data-result-filter="FAIL" title="FAIL" aria-label="FAIL">
<svg viewBox="0 0 24 24" width="17" height="17" fill="none" stroke="currentColor" stroke-width="2"><path d="M18 6 6 18"></path><path d="m6 6 12 12"></path></svg>
</button>
<button type="button" class="filter-btn filter-icon-btn detail-filter-btn" onclick="showCumplimientoDetailModal(); openGlobalModal();" title="Detalle Cumplimiento" aria-label="Detalle Cumplimiento">
<svg viewBox="0 0 24 24" width="17" height="17" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 3v18h18"></path><path d="M7 14l3-3 3 2 5-6"></path></svg>
</button>
</div>
</div>
<div class="table-responsive">
<table id="myTable" class="report-table">
<thead>
<tr>{"".join([f"<th>{html.escape(c)}</th>" for c in columns])}</tr>
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


# ========================================================================================
promedio_score = round(df["score_total"].mean(), 2) if len(df) > 0 else 0.0
date_str = datetime.now().strftime("%d%m%Y_%H%M%S")

tres_card_html = f"""
<div class="premium-stats-grid">
<div class="premium-card">
<div class="premium-card-icon icon-total">🪄</div>
<div class="premium-card-label">Total Casos</div>
<div class="premium-card-value">{total_cases}</div>
<div class="premium-card-sub">Escenarios evaluados</div>
</div>
<div class="premium-card">
<div class="premium-card-icon icon-pass">✅</div>
<div class="premium-card-label">PASS</div>
<div class="premium-card-value value-pass">{total_pass}</div>
<div class="premium-card-sub">{pass_percent}% del total</div>
</div>
<div class="premium-card">
<div class="premium-card-icon icon-warning">!</div>
<div class="premium-card-label">WARNING</div>
<div class="premium-card-value value-warning">{total_warning}</div>
<div class="premium-card-sub">{warning_percent}% del total</div>
</div>
<div class="premium-card">
<div class="premium-card-icon icon-fail">❌</div>
<div class="premium-card-label">FAIL</div>
<div class="premium-card-value value-fail">{total_fail}</div>
<div class="premium-card-sub">{fail_percent}% del total</div>
</div>
<div class="premium-card premium-card-donut">
<div class="donut-wrap">
<div class="donut-chart" style="background: conic-gradient(#16a34a 0 {pass_percent}%, #f59e0b {pass_percent}% {pass_warning_percent}%, #ef4444 {pass_warning_percent}% 100%);">
<div class="donut-center">{total_cases}</div>
</div>
<div class="donut-legend">
<div><span class="dot dot-pass"></span> PASS: {total_pass}</div>
<div><span class="dot dot-warning"></span> WARNING: {total_warning}</div>
<div><span class="dot dot-fail"></span> FAIL: {total_fail}</div>
<div>Éxito: {pass_percent}%</div>
</div>
</div>
</div>
<div class="premium-card premium-card-score">
<div class="premium-card-icon icon-score">📊</div>
<div class="premium-card-label premium-white">Puntuación Promedio</div>
<div class="premium-card-value premium-white">{promedio_score:.2f} / 1.00</div>
<div class="premium-card-sub premium-white-soft">Calidad agregada del agente</div>
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
               Generado: {datetime.now().strftime('%d-%m-%Y %H:%M:%S')} &nbsp;|&nbsp; Umbral Global: 80% &nbsp;|&nbsp; Casos De Prueba: {total_cases} &nbsp;|&nbsp; Tiempo Ejecución: {total_exec_time_formatted}
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
       --yellow-1: #d97706;
       --yellow-2: #f59e0b;
       --red-1: #dc2626;
       --red-2: #ef4444;
   }}
   *, *::before, *::after {{
       box-sizing: border-box;
   }}
   html, body {{
       min-height: 100%;
       width: 100%;
       overflow-x: hidden;
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
       font-size: clamp(20px, 2vw, 26px);
       margin: 0 0 8px 0;
       line-height: 1.2;
   }}
   .premium-header-sub {{
       color: #e3eafd;
       font-size: 14px;
       line-height: 1.55;
       overflow-wrap: anywhere;
   }}
   .premium-stats-grid {{
       display: grid;
       grid-template-columns: repeat(auto-fit, minmax(190px, 1fr));
       gap: 16px;
       margin: 24px 0 26px 0;
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
   .icon-warning {{
       background: linear-gradient(135deg, #fef3c7, #fbbf24);
       color: #92400e;
       font-weight: 900;
   }}
   .icon-fail {{
       background: linear-gradient(135deg, #fee2e2, #fca5a5);
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
       font-size: clamp(30px, 3.2vw, 46px);
       font-weight: 800;
       line-height: 1.05;
       color: #0f172a;
       overflow-wrap: anywhere;
   }}
   .premium-card-sub {{
       margin-top: 8px;
       font-size: 14px;
       color: #64748b;
   }}
   .value-pass {{
       color: #16a34a;
   }}
   .value-warning {{
       color: #d97706;
   }}
   .value-fail {{
       color: #dc2626;
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
   .dot-warning {{
       background: #f59e0b;
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
       flex-wrap: wrap;
   }}
   .result-filter {{
       display: flex;
       gap: 10px;
       align-items: center;
       justify-content: flex-end;
       flex-wrap: wrap;
   }}
   .filter-btn {{
       border: 1px solid #dbe3ef;
       border-radius: 12px;
       background: white;
       color: #0f172a;
       cursor: pointer;
       font-size: 13px;
       font-weight: 800;
       min-width: 74px;
       padding: 11px 16px;
       box-shadow: 0 8px 18px rgba(15, 23, 42, 0.06);
       transition: all .18s ease;
   }}
   .filter-icon-btn {{
       width: 42px;
       height: 42px;
       min-width: 42px;
       padding: 0;
       display: inline-flex;
       align-items: center;
       justify-content: center;
   }}
   .detail-filter-btn {{
       color: #1e3a8a;
       border-color: #bfd4ff;
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
       min-width: 1180px;
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
   .badge-warning {{
       display: inline-block;
       padding: 7px 14px;
       border-radius: 999px;
       background: linear-gradient(135deg, #d97706, #f59e0b);
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
   .score-wrap {{
       display: flex;
       flex-direction: column;
       gap: 6px;
       align-items: center;
   }}
   .score-status-wrap {{
       min-width: 128px;
   }}
   .score-status {{
       display: inline-flex;
       align-items: center;
       justify-content: center;
       min-width: 118px;
       border-radius: 999px;
       padding: 7px 10px;
       color: white;
       font-size: 12px;
       font-weight: 900;
       line-height: 1;
       text-align: center;
       white-space: nowrap;
   }}
   .score-status-pass {{
       background: linear-gradient(135deg, #16a34a, #22c55e);
   }}
   .score-status-warning {{
       background: linear-gradient(135deg, #d97706, #f59e0b);
   }}
   .score-status-fail {{
       background: linear-gradient(135deg, #dc2626, #ef4444);
   }}
   .metric-score {{
       display: inline-flex;
       min-width: 58px;
       justify-content: center;
       border-radius: 999px;
       padding: 6px 10px;
       font-weight: 900;
       font-size: 13px;
   }}
   .metric-score-good,
   .metric-score-pass {{
       background: #dcfce7;
       color: #15803d;
   }}
   .metric-score-warning {{
       background: #fef3c7;
       color: #b45309;
   }}
   .metric-score-bad,
   .metric-score-fail {{
       background: #fee2e2;
       color: #b91c1c;
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
       height: min(820px, calc(100vh - 64px));
       max-height: calc(100vh - 64px);
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
       gap: 12px;
       justify-content: flex-end;
   }}
   .modal-back-btn {{
       border: 1px solid #dbe3ef;
       border-radius: 10px;
       background: white;
       color: #174ea6;
       cursor: pointer;
       font-weight: 800;
       padding: 10px 18px;
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
       .donut-wrap {{
           flex-direction: column;
           align-items: flex-start;
       }}
       body {{
           padding: 14px;
       }}
       .premium-header {{
           border-radius: 18px;
           padding: 20px 18px;
       }}
       .premium-card {{
           border-radius: 18px;
           min-height: 128px;
           padding: 18px;
       }}
       .footer-fixed {{
           position: static;
           margin-top: 18px;
           border-radius: 14px;
       }}
       .table-card-header,
       .table-controls {{
           align-items: stretch;
           flex-direction: column;
           padding-left: 14px;
           padding-right: 14px;
       }}
       .result-filter,
       .table-pagination {{
           justify-content: flex-start;
       }}
       .filter-btn {{
           flex: 1 1 92px;
           min-width: 0;
       }}
       .filter-icon-btn {{
           flex: 0 0 42px;
           min-width: 42px;
       }}
       .table-responsive {{
           overflow-x: visible;
           padding: 0 12px 12px;
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
           box-shadow: 0 8px 20px rgba(15, 23, 42, 0.06);
           padding: 12px;
       }}
       #myTable td {{
           display: grid;
           grid-template-columns: minmax(110px, 42%) minmax(0, 1fr);
           align-items: center;
           gap: 10px;
           min-height: 44px;
           padding: 10px 0 !important;
           text-align: right;
           border-bottom: 1px solid #eef2f7 !important;
           overflow-wrap: anywhere;
       }}
       #myTable td:last-child {{
           border-bottom: 0 !important;
       }}
       #myTable td::before {{
           content: attr(data-label);
           color: #64748b;
           font-size: 11px;
           font-weight: 900;
           letter-spacing: .02em;
           text-align: left;
           text-transform: uppercase;
       }}
       .td-ellipsis {{
           max-width: none;
           white-space: normal;
           overflow: visible;
           text-overflow: clip;
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
           flex-wrap: wrap;
       }}
       .modal {{
           align-items: stretch;
           padding: 8px;
       }}
       .modal-dialog {{
           width: 100%;
           height: calc(100vh - 16px);
           max-height: calc(100vh - 16px);
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
           min-width: 0;
           overflow: hidden;
           text-overflow: ellipsis;
           white-space: nowrap;
           font-size: 16px;
       }}
       .modal-rich-content,
       .modal-viewer {{
           padding: 14px;
       }}
       .modal-footer {{
           padding: 12px 14px;
           flex-direction: column-reverse;
       }}
       .modal-back-btn,
       .modal-close-btn {{
           width: 100%;
       }}
       .conversation-message {{
           padding: 12px;
       }}
       .conversation-text,
       .metric-card-desc,
       .metric-summary-text {{
           overflow-wrap: anywhere;
       }}
       .data-pre {{
           white-space: pre-wrap;
           overflow-wrap: anywhere;
           padding: 14px;
           font-size: 12px;
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
.metric-cards-grid {{
   display: grid;
   grid-template-columns: repeat(2, 1fr);
   gap: 14px;
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
.metric-card-score-good {{
   background: #dcfce7;
   color: #15803d;
}}
.metric-card-score-warning {{
   background: #fef3c7;
   color: #b45309;
}}
.metric-card-score-fail {{
   background: #fee2e2;
   color: #b91c1c;
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
.compliance-detail-report {{
   max-width: 1060px;
   margin: 0 auto;
   background: white;
   border: 1px solid #dbe3ef;
   border-radius: 16px;
   padding: 22px;
   box-shadow: 0 8px 22px rgba(15, 23, 42, 0.06);
}}
.compliance-report-title {{
   color: #0f172a;
   font-size: 15px;
   font-weight: 900;
   margin: 0 0 12px 0;
   text-transform: uppercase;
}}
.compliance-summary-table,
.compliance-detail-table {{
   width: 100%;
   border-collapse: collapse;
   background: white;
   font-size: 13px;
}}
.compliance-summary-table {{
   max-width: 720px;
   margin-bottom: 30px;
}}
.compliance-summary-table th,
.compliance-summary-table td,
.compliance-detail-table th,
.compliance-detail-table td {{
   border: 1px solid #cbd5e1;
   padding: 9px 10px;
   text-align: center;
   vertical-align: middle;
}}
.compliance-summary-table th,
.compliance-detail-table th {{
   color: #0f172a;
   font-size: 12px;
   font-weight: 900;
   text-transform: uppercase;
}}
.compliance-count-btn {{
   min-width: 84px;
   border: 0;
   border-radius: 10px;
   background: #eef4ff;
   color: #174ea6;
   cursor: pointer;
   font-size: 16px;
   font-weight: 900;
   padding: 9px 16px;
   transition: all .18s ease;
}}
.compliance-count-btn:hover {{
   transform: translateY(-1px);
   box-shadow: 0 8px 18px rgba(30, 64, 175, 0.14);
}}
.compliance-count-fail {{
   color: #b91c1c;
   background: #fee2e2;
}}
.compliance-count-warning {{
   color: #b45309;
   background: #fef3c7;
}}
.compliance-count-pass {{
   color: #15803d;
   background: #dcfce7;
}}
.summary-fail {{
   background: #fee2e2;
   color: #991b1b !important;
}}
.summary-warning {{
   background: #fef3c7;
   color: #92400e !important;
}}
.summary-pass {{
   background: #dcfce7;
   color: #166534 !important;
}}
.compliance-section {{
   margin-top: 24px;
}}
.compliance-section h4 {{
   color: #0f172a;
   font-size: 13px;
   font-weight: 900;
   margin: 0 0 10px 0;
   text-transform: uppercase;
}}
.compliance-table-wrap {{
   overflow-x: auto;
   scrollbar-gutter: stable;
}}
.compliance-detail-table {{
   min-width: 760px;
}}
.compliance-detail-table th {{
   background: #f8fbff;
}}
.compliance-text-cell {{
   max-width: 360px;
   text-align: left !important;
   color: #334155;
   line-height: 1.45;
}}
.compliance-score-cell {{
   width: 120px;
}}
.compliance-row.compliance-fail {{
   background: #fff7f7;
}}
.compliance-row.compliance-warning {{
   background: #fffbeb;
}}
.compliance-row.compliance-pass {{
   background: #f7fff9;
}}
.compliance-empty {{
   color: #64748b;
   font-style: italic;
   text-align: center;
}}
.compliance-scenarios-report {{
   max-width: 1060px;
   margin: 0 auto;
}}
.compliance-scenarios-count {{
   color: #0f172a;
   font-size: 18px;
   font-weight: 900;
   margin: 0 0 18px 0;
}}
.compliance-scenarios-table {{
   background: white;
   border-radius: 16px;
   overflow: hidden;
}}
@media (max-width: 900px) {{
   .metric-cards-grid {{
       grid-template-columns: 1fr;
   }}
}}
@media (max-width: 768px) {{
   .modal-rich-content,
   .modal-viewer {{
       padding: 14px;
   }}
   .conversation-message {{
       padding: 12px;
   }}
   .conversation-text,
   .metric-card-desc,
   .metric-summary-text,
   .compliance-text-cell {{
       overflow-wrap: anywhere;
   }}
   .data-pre {{
       white-space: pre-wrap;
       overflow-wrap: anywhere;
       padding: 14px;
       font-size: 12px;
   }}
   .metric-card-header {{
       align-items: flex-start;
       gap: 10px;
   }}
   .metric-card-title {{
       min-width: 0;
       overflow-wrap: anywhere;
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
            <button type="button" class="modal-back-btn" id="modalBackBtn" onclick="showCumplimientoDetailModal()" style="display:none;">Volver</button>
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
function metricCardScoreClass(nombre, valor) {{
   const n = Number(valor || 0);
   const metricName = String(nombre || "").toUpperCase();
   if (metricName.includes("CUMPLIMIENTO")) {{
       if (n <= 0.35) return "metric-card-score-fail";
       if (n <= 0.80) return "metric-card-score-warning";
       return "metric-card-score-good";
   }}
   return n >= 0.80 ? "metric-card-score-good" : "metric-card-score-fail";
}}
function renderMetricCard(nombre, valor, descripcion){{
   const scoreClass = metricCardScoreClass(nombre, valor);
   return `
<div class="metric-card">
<div class="metric-card-header">
<div class="metric-card-title">${{escaparHtml(nombre)}}</div>
<div class="metric-card-score ${{scoreClass}}">${{Number(valor || 0).toFixed(2)}}</div>
</div>
<div class="metric-card-desc">${{escaparHtml(descripcion || "")}}</div>
</div>
`;
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

function setModalBackVisible(visible) {{
   const backBtn = document.getElementById('modalBackBtn');
   if (!backBtn) return;
   backBtn.style.display = visible ? 'inline-flex' : 'none';
}}

function showCumplimientoDetailModal() {{
   let textContent = document.getElementById('uniqueModalTextContent');
   let rich = document.getElementById('uniqueModalRichContent');
   let lbl = document.getElementById('uniqueModalTitle');
   if (!textContent || !rich || !lbl) return;
   lbl.textContent = 'DETALLE CUMPLIMIENTO';
   setModalBackVisible(false);
   textContent.style.display = "none";
   rich.style.display = "block";
   textContent.textContent = "";
   rich.innerHTML = window.__CUMPLIMIENTO_DETAIL__ || '<div class="compliance-detail-report">Sin contenido.</div>';
   rich.scrollTop = 0;
}}

function showCumplimientoStatusModal(status) {{
   let textContent = document.getElementById('uniqueModalTextContent');
   let rich = document.getElementById('uniqueModalRichContent');
   let lbl = document.getElementById('uniqueModalTitle');
   if (!textContent || !rich || !lbl) return;
   const key = String(status || '').toUpperCase();
   const detail = window.__CUMPLIMIENTO_GROUP_DETAILS__ && window.__CUMPLIMIENTO_GROUP_DETAILS__[key];
   lbl.textContent = detail && detail.titulo ? detail.titulo : 'Escenarios Por Cumplimiento';
   setModalBackVisible(true);
   textContent.style.display = "none";
   rich.style.display = "block";
   textContent.textContent = "";
   rich.innerHTML = detail && detail.html ? detail.html : '<div class="compliance-scenarios-report">Sin contenido.</div>';
   rich.scrollTop = 0;
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
   setModalBackVisible(false);
   textContent.style.display = "block";
   rich.style.display = "none";
   textContent.textContent = "";
   rich.innerHTML = "";
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
   if (tipo === "detalle_metricas" && typeof contenido === "object" && contenido !== null) {{
       textContent.style.display = "none";
       rich.style.display = "block";
       const htmlMetricas = `
<div class="metric-cards-grid">
               ${{renderMetricCard("Cumplimiento",(contenido.cumplimiento || [0])[0], (contenido.cumplimiento || ["", ""])[1])}}
               ${{renderMetricCard("Coherencia", (contenido.coherencia || [0])[0], (contenido.coherencia || ["", ""])[1])}}
               ${{renderMetricCard("Fluidez", (contenido.fluidez || [0])[0], (contenido.fluidez || ["", ""])[1])}}
               ${{renderMetricCard("Integridad", (contenido.integridad || [0])[0], (contenido.integridad || ["", ""])[1])}}
               ${{renderMetricCard("Claridad", (contenido.claridad || [0])[0], (contenido.claridad || ["", ""])[1])}}
               ${{renderMetricCard("Corrección", (contenido.correccion || [0])[0], (contenido.correccion || ["", ""])[1])}}
</div>
<div class="metric-summary-box">
<div class="metric-summary-title">Resumen general</div>
<div class="metric-summary-text">${{escaparHtml(contenido.justificacion || "")}}</div>
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
   setModalBackVisible(false);
   document.body.classList.remove('modal-open');
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

   const rows = Array.from(table.querySelectorAll('tbody tr'));
   const filterButtons = Array.from(document.querySelectorAll('[data-result-filter]'));
   const tableInfo = document.getElementById('tableInfo');
   const pagination = document.getElementById('tablePagination');
   let activeFilter = 'TODOS';
   let currentPage = 1;

   function normalizeResult(value) {{
       const normalized = String(value || '').trim().toUpperCase();
       if (normalized === 'PASS' || normalized === 'SUCCESS' || normalized === 'CUMPLE') return 'PASS';
       if (normalized === 'WARNING' || normalized === 'PARCIALMENTE') return 'WARNING';
       if (normalized === 'FAIL' || normalized === 'NO CUMPLE') return 'FAIL';
       return normalized;
   }}

   function getFilteredRows() {{
       return rows.filter(function(row) {{
           if (activeFilter === 'TODOS') return true;
           return normalizeResult(row.getAttribute('data-result')) === activeFilter;
       }});
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
           activeFilter = btn.getAttribute('data-result-filter') || 'TODOS';
           currentPage = 1;
           filterButtons.forEach(function(item) {{
               item.classList.remove('active');
           }});
           btn.classList.add('active');
           renderTable();
       }});
   }});

   renderTable();
}});

</script>
</body>
</html>
"""

date_str = datetime.now().strftime("%d%m%Y_%H%M%S")
report_name = f"simulador_con_juez_{date_str}.html"
report_path = os.path.join(OUTPUT_DIR, report_name)
with open(report_path, "w", encoding="utf-8") as f:
    f.write(html_doc)
print("Reporte HTML generado:", report_path)
csv_name = report_name.replace(".html", ".csv")
csv_path = os.path.join(OUTPUT_DIR, csv_name)
df.to_csv(csv_path, index=False, sep=";", encoding="utf-8-sig")
print("CSV generado:", csv_path)

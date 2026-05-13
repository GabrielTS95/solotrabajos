import os
import json
import html
import requests
import pandas as pd
import dotenv
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
CSV_PATH = r"D:\Datos de Usuarios\T76960\Squad Phoenix\auto-phoenix\escenarios_funcionalidades_especificas.csv"
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
        NOMBRE_COMPLETO=nombre_completo or "XXXXXX",
        DEUDA_SOLES=deuda_soles or "XXXXXX",
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
    resp = client.chat.completions.create(
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


def llm_judge_metricas(
    question: str, caso_de_prueba: str = "", reglas_juez: str = "", model=MODEL_NAME
):
    prompt = f"""
Eres un evaluador experto en pruebas de negocio de cobranzas digitales.
Debes evaluar la siguiente conversación entre el AGENTE (BOT) y el CLIENTE.
Debes centrarte EXCLUSIVAMENTE en lo que se indica en 'REGLAS DEL JUEZ' y en el 'CASO DE PRUEBA'.
CASO DE PRUEBA:
{caso_de_prueba or 'Sin caso de prueba definido.'}
REGLAS DEL JUEZ:
{reglas_juez or 'Sin reglas para este caso.'}
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
- Cada métrica debe estar entre 0.00 y 1.00
- score_total es el promedio de todas las métricas
- resultado = "PASS" si score_total >= 0.80, si no "FAIL"
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
    response = client.chat.completions.create(
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
        promedio = round(
            (
                m_coherencia
                + m_fluidez
                + m_cumplimiento
                + m_integridad
                + m_claridad
                + m_correccion
            )
            / 6,
            2,
        )
        score_total = sf(parsed.get("score_total", promedio))
        resultado = "PASS" if score_total >= 0.80 else "FAIL"
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
    mapa_classification = {"I": "3", "AR": "4", "R": "2"}
    mapa_segments = {
        "PY_1": "pyme",
        "PY_2": "pyme",
        "PE_1": "personas",
        "PE_2": "personas",
        "PE_3": "personas",
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
    segmento_persona = tipo_seg_csv in ("PE_1", "PE_2", "PE_3")
    segmento_pyme = tipo_seg_csv in ("PY_1", "PY_2") or not tipo_seg_csv

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
        # Otros casos
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
    tipo_cliente_csv = safe_str(user_row.get("tipo_cliente")).upper()
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
        if tipo_seg_norm in ("PE_1", "PE_2", "PE_3"):
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

    # Deuda soles
    deuda_soles_csv = safe_str(user_row.get("deuda_soles"))
    val_debt_amount_1 = (
        float(deuda_soles_csv)
        if deuda_soles_csv
        else round(fake.pyfloat(right_digits=2, min_value=500, max_value=15000), 2)
    )
    val_currency1 = "PEN"

    # Cuenta 1
    accnum1 = fake.bothify(text="#####-###-####", letters="")

    # Deuda dólares
    deuda_dolares_csv = safe_str(user_row.get("deuda_dolares"))
    val_debt_amount_2 = float(deuda_dolares_csv) if deuda_dolares_csv else 0.0
    val_currency2 = "USD"
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
    last_pdp = last_pdp_csv if last_pdp_csv else fake.random_element(["Si", "No"])

    # active_pkg
    active_pkg = safe_str(user_row.get("active_pkg")) or "No"
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
            # NUEVOS CAMPOS EN customer_data
            "profile_quadrant": profile_quadrant,
            "cod_customer_priority": cod_customer_priority,
            "customer_type": customer_type,
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
        },
    }

    print(
        "Payload generado para la fila:",
        json.dumps(payload, indent=2, ensure_ascii=False),
    )
    return payload


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
    # ... genera df y calcula total_exec_time_formatted
total_exec_time_formatted = format_td_hms(total_exec_time)
df = pd.DataFrame(rows)
print(df.head())


# Contadores escenarios PASS y FAIL y su porcentaje sobre el total
total_cases = len(df)
total_pass = df["status_prueba"].astype(str).str.upper().eq("PASS").sum()
total_fail = df["status_prueba"].astype(str).str.upper().eq("FAIL").sum()
pass_percent = round((total_pass / total_cases) * 100) if total_cases else 0
fail_percent = round((total_fail / total_cases) * 100) if total_cases else 0


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
<summary><i class="bi bi-eye"></i> Visualizar</summary>
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
       data-bs-toggle="modal" data-bs-target="#uniqueGlobalModal"
       data-content-idx="{idx}"
       data-content-tipo="{tipo}"
       data-title="{titulo_safe}"
       onclick="showUniqueModalFromButton(this)"
       title="{titulo_safe}">
       {icon_svg}
</button>
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
    score = float(r.get("score_total", 0))
    status = safe_str(r.get("status_prueba")).upper()
    badge = (
        "<span class='badge-pass'>PASS</span>"
        if status == "PASS"
        else "<span class='badge-fail'>FAIL</span>"
    )
    score_class = "score-pass" if status == "PASS" else "score-fail"
    score_pct = max(0, min(100, round(score * 100)))
    row_html = f"""
<tr>
<td>{escape_cell(r.get("id_test"))}</td>
<td class="td-ellipsis" title="{escape_cell(r.get('caso_de_prueba'))}">
           {html.escape(resumir_texto(r.get("caso_de_prueba"), 42))}
</td>
<td>{float(r.get("m_cumplimiento", 0)):.2f}</td>
<td>{float(r.get("m_coherencia", 0)):.2f}</td>
<td>{float(r.get("m_fluidez", 0)):.2f}</td>
<td>{float(r.get("m_integridad", 0)):.2f}</td>
<td>{float(r.get("m_claridad", 0)):.2f}</td>
<td>{float(r.get("m_correccion", 0)):.2f}</td>
<td>
<div class="score-wrap">
<div class="{score_class}">{score:.2f}</div>
<div class="score-bar">
<div class="score-fill {'fill-pass' if status == 'PASS' else 'fill-fail'}" style="width:{score_pct}%"></div>
</div>
</div>
</td>
<td>{badge}</td>
<td>
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
    + ";\n</script>"
)

html_table = f"""
<div class="table-card">
<div class="table-title">Resultados por Escenario</div>
<div class="table-responsive">
<table id="myTable" class="table table-hover align-middle">
<thead>
<tr>{"".join([f"<th>{html.escape(c)}</th>" for c in columns])}</tr>
</thead>
<tbody>
               {''.join(html_tablerows)}
</tbody>
</table>
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
<div class="premium-card-icon icon-fail">❌</div>
<div class="premium-card-label">FAIL</div>
<div class="premium-card-value value-fail">{total_fail}</div>
<div class="premium-card-sub">{fail_percent}% del total</div>
</div>
<div class="premium-card premium-card-donut">
<div class="donut-wrap">
<div class="donut-chart" style="background: conic-gradient(#16a34a 0 {pass_percent}%, #ef4444 {pass_percent}% 100%);">
<div class="donut-center">{total_cases}</div>
</div>
<div class="donut-legend">
<div><span class="dot dot-pass"></span> PASS: {total_pass}</div>
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
               Generado: {datetime.now().strftime('%d-%m-%Y %H:%M:%S')} &nbsp;|&nbsp; Umbral Global: 80% &nbsp;|&nbsp; Casos De Prueba: {total_cases}
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
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/js/bootstrap.bundle.min.js"></script>
<link rel="stylesheet" type="text/css" href="https://cdn.datatables.net/1.11.5/css/jquery.dataTables.css">
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
   }}
   body {{
       font-family: "Segoe UI", Arial, sans-serif;
       margin: 0;
       padding: 24px 24px 100px 24px;
       background: linear-gradient(180deg, var(--bg-1) 0%, var(--bg-2) 100%);
       color: #1f2937;
   }}
   .page-container {{
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
   }}
   .premium-stats-grid {{
       display: grid;
       grid-template-columns: repeat(5, 1fr);
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
   }}
   .table-title {{
       padding: 22px 24px 10px 24px;
       font-size: 20px;
       font-weight: 800;
       color: #1e3a8a;
   }}
   #myTable {{
       width: 100% !important;
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
   .modal-content {{
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
   }}
   .modal-title {{
       font-weight: 800;
       font-size: 20px;
   }}
   .btn-close {{
       filter: brightness(0) invert(1);
   }}
   .modal-body {{
       padding: 22px;
       background: #f8fbff;
   }}
   .modal-viewer {{
       width: 100%;
       min-height: 420px;
       max-height: 58vh;
       border-radius: 16px;
       border: 1px solid #dbe3ef;
       background: white;
       color: #334155;
       font-family: Consolas, Monaco, monospace;
       font-size: 14px;
       line-height: 1.7;
       padding: 18px;
       resize: none;
       outline: none;
       white-space: pre-wrap;
       overflow: auto;
   }}
   .modal-footer {{
       border-top: 1px solid #e5e7eb;
       background: white;
       padding: 14px 22px;
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
   .dataTables_wrapper .dataTables_filter,
   .dataTables_wrapper .dataTables_length {{
       display: none !important;
   }}
   .dataTables_wrapper .dataTables_info {{
       font-size: 12px;
       color: #64748b;
       padding: 14px 20px;
   }}
   .dataTables_wrapper .dataTables_paginate {{
       padding: 12px 18px 18px 18px;
   }}
   .dataTables_wrapper .dataTables_paginate .paginate_button {{
       border-radius: 10px !important;
       border: 1px solid #dbe3ef !important;
       background: white !important;
       color: #334155 !important;
       margin: 0 3px !important;
   }}
   .dataTables_wrapper .dataTables_paginate .paginate_button.current {{
       background: linear-gradient(135deg, #2563eb, #3b82f6) !important;
       color: white !important;
       border: none !important;
   }}
   @media (max-width: 1300px) {{
       .premium-stats-grid {{
           grid-template-columns: repeat(2, 1fr);
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
           padding: 14px 14px 100px 14px;
       }}
       .footer-fixed {{
           left: 14px;
           right: 14px;
       }}
   }}

   .modal-rich-content {{
   display: block;
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





</style>
{html_modal_contents}
</head>
<body>
<div class="page-container">
   {cabecera_html}
   {tres_card_html}
   {html_table}
</div>

<div class="modal fade" id="uniqueGlobalModal" tabindex="-1" aria-labelledby="uniqueModalTitle" aria-hidden="true">
   <div class="modal-dialog modal-xl modal-dialog-centered">
      <div class="modal-content">
         <div class="modal-header">
            <h5 class="modal-title" id="uniqueModalTitle">Detalle</h5>
            <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
         </div>
         <div class="modal-body">
            <div id="uniqueModalRichContent" class="modal-rich-content" style="display:none;"></div>
            <textarea id="uniqueModalTextarea" class="modal-viewer" readonly></textarea>
         </div>
         <div class="modal-footer">
            <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cerrar</button>
         </div>
      </div>
   </div>
</div>

<div class="footer-fixed">
   Programa IA Credicorp | Área de Quality Engineer | Squad de Agente |
<strong>© 2026 Todos los Derechos Reservados.</strong>
</div>
<script src="https://code.jquery.com/jquery-3.6.0.min.js"></script>
<script type="text/javascript" charset="utf8" src="https://cdn.datatables.net/1.11.5/js/jquery.dataTables.js"></script>

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
function renderMetricCard(nombre, valor, descripcion){{
   return `
<div class="metric-card">
<div class="metric-card-header">
<div class="metric-card-title">${{escaparHtml(nombre)}}</div>
<div class="metric-card-score">${{Number(valor || 0).toFixed(2)}}</div>
</div>
<div class="metric-card-desc">${{escaparHtml(descripcion || "")}}</div>
</div>
`;
}}

function showUniqueModalFromButton(btn) {{
   let ta = document.getElementById('uniqueModalTextarea');
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
   ta.style.display = "block";
   rich.style.display = "none";
   ta.value = "";
   rich.innerHTML = "";
   if (tipo === "detalle_metricas" && typeof contenido === "object" && contenido !== null) {{
       ta.style.display = "none";
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
   ta.value = contenido || '';
}}

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

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
    "",
)
AZURE_OPENAI_API_VERSION = os.getenv(
    "AZURE_OPENAI_API_VERSION","",
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
    r"D:\Datos de Usuarios\T76960\Squad Phoenix\auto-phoenix\escenarios_funcionalidades_especificas.csv",
)
# CSV_PATH = r"D:\Datos de Usuarios\T76960\Squad Phoenix\auto-phoenix\escenarios_martin_2.csv"
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
# LLAMAR AL JUEZ - NUEVO JUEZ POR FUNCIONALIDADES
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
    ("coherencia", "Coherencia"),
    ("contexto", "Contexto"),
    ("claridad", "Claridad"),
    ("fluidez", "Fluidez"),
    ("alucinacion", "Alucinación"),
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

def get_prompt_juez(question, perfil, reglas_juez=None):

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


def llm_judge_metricas(
        question: str, perfil: str = "", reglas_juez: str = "", model=MODEL_NAME
):
    prompt = get_prompt_juez(question=question, perfil=perfil, reglas_juez=reglas_juez)

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
        max_tokens=2500,
        temperature=0,
    )

    latency_s = round((datetime.now() - t0).total_seconds(), 2)
    content = (response.choices[0].message.content or "").strip()

    try:
        content_clean = content.replace("```json", "").replace("```", "").strip()

        start = content_clean.find("{")
        end = content_clean.rfind("}")

        if start == -1 or end == -1:
            raise ValueError("La respuesta del juez no contiene un JSON válido.")

        parsed = json.loads(content_clean[start: end + 1])

        result = {}

        for key, _ in FUNCIONALIDADES_JUEZ:
            score_key = f"{key}_score"
            just_key = f"{key}_justification"

            result[score_key] = normalizar_score_funcionalidad(parsed.get(score_key, 0))
            result[just_key] = safe_str(parsed.get(just_key, ""))

        result["raw_json"] = json.dumps(parsed, ensure_ascii=False, indent=2)
        result["latencia_eval_s"] = latency_s

        return calcular_resumen_funcionalidades(result)



    except Exception as e:
        return build_error_juez_result(
            motivo=f"Error analizando salida del juez: {type(e).__name__}: {e}",
            raw_json=content,
            latency_s=latency_s,
        )


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

    # Deuda soles     deuda_soles_csv = saf... de Erwin Torres
    # Erwin Torres

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
        perfil_juez,
        scenario_exec_time,
):
    row = {
        "_orden_csv": orden_csv,
        "_scenario_seconds": scenario_exec_time.total_seconds(),
        "id_test": safe_str(user.get("id_test")),
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
    conversa = []
    status = "OK"
    bot_turns = 0
    last_bot = ""
    total_bot_latency_s = 0.0
    total_sim_latency_s = 0.0
    full_conversation = ""
    perfil_juez = ""

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
        full_conversation = build_full_conversation(conversa)

    try:
        perfil_juez = safe_str(
            request_cliente_json.get("customer_data", {}).get("classification", "")
        )

        eval_juez = llm_judge_metricas(
            question=full_conversation, perfil=perfil_juez, reglas_juez=reglas_juez
        )

    except Exception as e:
        eval_juez = build_error_juez_result(
            motivo=f"Excepción ejecutando juez: {type(e).__name__}: {e}",
            raw_json="{}",
            latency_s=0.0,
        )

    row = construir_row_resultado(
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
        perfil_juez,
        scenario_exec_time,
    )

    return row


def ejecutar_escenarios_secuencial(df_escenarios):
    total_escenarios = len(df_escenarios)
    if total_escenarios == 0:
        return [], timedelta(0)

    print(f"[INFO] Ejecutando {total_escenarios} escenarios en modo secuencial.")

    rows_resultado = []
    for orden_csv, (_, user) in enumerate(df_escenarios.iterrows()):
        rows_resultado.append(ejecutar_escenario_phoenix(orden_csv, user.copy()))
        print(f"[PROGRESO] {orden_csv + 1}/{total_escenarios} escenarios completados")

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
rows, total_exec_time = ejecutar_escenarios_secuencial(df_users_ejecutar)
global_end = datetime.now()
wall_exec_time = global_end - global_start
total_exec_time_formatted = format_td_hms(total_exec_time)
wall_exec_time_formatted = format_td_hms(wall_exec_time)
df = pd.DataFrame(rows)
print(df.head())

# Contadores escenarios PASS y FAIL y su porcentaje sobre el total
total_cases = len(df)
total_pass = df["status_prueba"].astype(str).str.upper().eq("PASS").sum()
total_fail = df["status_prueba"].astype(str).str.upper().eq("FAIL").sum()
pass_percent = round((total_pass / total_cases) * 100) if total_cases else 0
fail_percent = round((total_fail / total_cases) * 100) if total_cases else 0


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

        filas.append(
            {
                "key": key,
                "funcionalidad": label,
                "cumple": cumple,
                "cumple_pct": calcular_porcentaje(cumple, total_escenarios),
                "no_cumple": no_cumple,
                "no_cumple_pct": calcular_porcentaje(no_cumple, total_escenarios),
                "no_aplica": no_aplica,
                "no_aplica_pct": calcular_porcentaje(no_aplica, total_escenarios),
                "aplica": aplica,
                "aplica_pct": calcular_porcentaje(aplica, total_escenarios),
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
    "Puntuación",
    "Tiempo Ejecución",
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

    detalle_metricas = {
        "metricas": [],
        "resumen": r.get("comentario_status_prueba", ""),
    }

    for key, label in FUNCIONALIDADES_VISIBLES_REPORTE:
        score = int(r.get(f"{key}_score", 0))
        justification = safe_str(r.get(f"{key}_justification", ""))

        if score == 1:
            estado = "CUMPLE"
        elif score == 0:
            estado = "NO CUMPLE"
        else:
            estado = "NO APLICA"

        detalle_metricas["metricas"].append(
            {
                "key": key,
                "label": label,
                "score": score,
                "estado": estado,
                "justification": justification,
            }
        )

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

    score = float(r.get("score_total", 0))
    status = safe_str(r.get("status_prueba")).upper()

    badge = (
        "<span class='badge-pass'>PASS</span>"
        if status == "PASS"
        else "<span class='badge-fail'>FAIL</span>"
    )

    score_class = "score-pass" if status == "PASS" else "score-fail"
    score_pct = max(0, min(100, round(score * 100)))

    metric_cells = ""

    for key, label in FUNCIONALIDADES_VISIBLES_REPORTE:
        metric_cells += f"<td data-label=\"{html.escape(label)}\">{badge_funcionalidad(r.get(f'{key}_score', 0))}</td>"

    row_html = f"""
<tr data-result="{status}">
<td data-label="Cod. Test">{escape_cell(r.get("id_test"))}</td>
<td data-label="Escenario" class="td-ellipsis" title="{escape_cell(r.get('caso_de_prueba'))}">
    {html.escape(resumir_texto(r.get("caso_de_prueba"), 42))}
</td>



{metric_cells}



<td data-label="Puntuacion">
<div class="score-wrap">
<div class="{score_class}">{score:.2f}</div>
<div class="score-bar">
<div class="score-fill {'fill-pass' if status == 'PASS' else 'fill-fail'}" style="width:{score_pct}%"></div>
</div>
</div>
</td>
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

# =========================================... de Erwin Torres
# Erwin Torres

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
           grid-template-columns: repeat(3, 48px);
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
           grid-template-columns: repeat(3, 48px);
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

   if (valor === 1) return "CUMPLE";
   if (valor === 0) return "NO CUMPLE";
   return "NO APLICA";
}}

function getClaseScore(valor) {{
   valor = Number(valor);

   if (valor === 1) return "badge-modal-cumple";
   if (valor === 0) return "badge-modal-no-cumple";
   return "badge-modal-no-aplica";
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
                    <th>Detalle de la metrica</th>
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

   let descripcion = item.justification || "";

   return `
<div class="metric-card">
<div class="metric-card-header">
<div class="metric-card-title">${{escaparHtml(nombre)}}</div>
<div class="metric-card-score ${{getClaseScore(valor)}}">${{escaparHtml(estado)}}</div>
</div>

    <div class="metric-score-line">
<strong>Puntaje:</strong> ${{valor}}
</div>

    <div class="metric-justification">
<strong>Justificación:</strong><br>

        ${{escaparHtml(descripcion)}}
</div>
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

   let metricas = contenido.metricas || [];
   let resumen = contenido.resumen || "";

   if (!Array.isArray(metricas) || metricas.length === 0) {{
       rich.innerHTML = `
<div class="metric-summary-box">
    <div class="metric-summary-title">Sin detalle de métricas</div>
    <div class="metric-summary-text">No se encontraron métricas para visualizar.</div>
</div>
`;
       return;
   }}

   let cards = "";

   metricas.forEach(function(item) {{
       cards += renderMetricCard(item);
   }});

   let htmlMetricas = `
<div class="metric-cards-grid">
    ${{cards}}
</div>

<div class="metric-summary-box">
    <div class="metric-summary-title">Resumen general</div>
    <div class="metric-summary-text">${{escaparHtml(resumen)}}</div>
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

   const rows = Array.from(table.querySelectorAll('tbody tr'));
   const filterButtons = Array.from(document.querySelectorAll('[data-result-filter]'));
   const tableInfo = document.getElementById('tableInfo');
   const pagination = document.getElementById('tablePagination');
   let activeFilter = 'TODOS';
   let currentPage = 1;

   function normalizeResult(value) {{
       const normalized = String(value || '').trim().toUpperCase();
       if (normalized === 'PASS' || normalized === 'SUCCESS') return 'SUCCESS';
       if (normalized === 'FAIL') return 'FAIL';
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
report_name = f"Rep-juez-funcionalidades-secuencial_{date_str}.html"
report_path = os.path.join(OUTPUT_DIR, report_name)
with open(report_path, "w", encoding="utf-8") as f:
    f.write(html_doc)
print("Reporte HTML generado:", report_path)
csv_name = report_name.replace(".html", ".csv")
csv_path = os.path.join(OUTPUT_DIR, csv_name)
df.to_csv(csv_path, index=False, sep=";", encoding="utf-8-sig")
print("CSV generado:", csv_path)

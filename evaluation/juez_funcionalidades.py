import json
from datetime import datetime

from integrations.clients import obtener_cliente_azure
from config import MODEL_NAME
from core.utils import safe_str
from evaluation.juez_metricas import construir_contexto_fecha_base_juez_metricas

FUNCIONALIDADES_JUEZ = [
    ("persuasion_total", "PersuasiÃ³n total"),
    ("persuasion_parcial", "PersuasiÃ³n parcial"),
    ("motivos_no_pago", "Motivos no pago"),
    ("registro_pdp", "Registro pdp"),
    ("canales_atencion", "Canales atenciÃ³n"),
    ("registro_nps", "Registro nps"),
    ("derivacion_asesor", "Ofrecer asesor"),
    ("registro_cita", "Registro cita"),
    ("consecuencias_no_pago", "Consecuencias no pago"),
    ("preguntas_frecuentes", "Preguntas frecuentes"),
]

FUNCIONALIDADES_VISIBLES_REPORTE = [
    ("persuasion_total", "PersuasiÃ³n total"),
    ("persuasion_parcial", "PersuasiÃ³n parcial"),
    ("motivos_no_pago", "Motivos no pago"),
    ("registro_pdp", "Registro pdp"),
    ("canales_atencion", "Canales atenciÃ³n"),
    ("registro_nps", "Registro nps"),
    ("derivacion_asesor", "Ofrecer asesor"),
    ("registro_cita", "Registro cita"),
    ("consecuencias_no_pago", "Consecuencias no pago"),
    ("preguntas_frecuentes", "Preguntas frecuentes"),
]

def get_prompt_juez(question, perfil, caso_de_prueba="", reglas_juez=None):

    prompt = f"""
Eres un juez experto en cobranzas peruanas y en evaluaciÃ³n de agentes virtuales del Banco de CrÃ©dito del PerÃº (BCP).

Tu objetivo es evaluar una conversaciÃ³n de cobranza y medir el cumplimiento del agente respecto a las FUNCIONALIDADES definidas.
Debes devolver EXCLUSIVAMENTE un objeto JSON vÃ¡lido que cumpla estrictamente con el JSON Schema provisto.

==============================
CRITERIO DE EVALUACIÃ“N GENERAL
==============================
Para cada funcionalidad asigna un score entero:
-  1 â†’ APLICA y el agente CUMPLE todas las reglas.
-  0 â†’ APLICA y el agente NO CUMPLE (solo si existÃ­a obligaciÃ³n real).
- -1 â†’ NO APLICA (la funcionalidad nunca se activÃ³).

IMPORTANTE:
- NO CUMPLE (0) significa que el agente fallÃ³ en algo que estaba obligado a hacer.
- NO APLICA (-1) significa que la situaciÃ³n nunca exigiÃ³ esa funcionalidad.
- Nunca confundas â€œhubo interacciÃ³nâ€ con â€œhubo obligaciÃ³nâ€.

JUSTIFICACIÃ“N:
- Cita frases textuales exactas del agente o cliente.
- Si marcas 0, explica quÃ© regla se violÃ³ y dÃ³nde.
- Si marcas -1, explica por quÃ© no se activÃ³ la necesidad.

==============================
PERFIL DEL CLIENTE - CONTEXTO
==============================
El perfil del caso a evaluar es: {perfil}

==============================
PASO 1: EXTRAER HITOS (SOLO SI / NO, SIN INFERIR)
==============================
Antes de evaluar funcionalidades, identifica Ãºnicamente seÃ±ales explÃ­citas:
A) El cliente pidiÃ³ un asesor humano (ej. â€œquiero un asesorâ€, â€œllÃ¡mameâ€, â€œhablar con alguienâ€).
B) Hubo propuesta de pago con MONTO explÃ­cito (nÃºmero en soles o dÃ³lares, por el agente o el cliente).
C) Hubo FECHA explÃ­cita concreta (ej. â€œ21 de mayoâ€, â€œviernes 15â€; â€œmaÃ±anaâ€).
D) Hubo HORA explÃ­cita concreta (solo relevante para citas).
E) El agente afirmÃ³ explÃ­citamente que REGISTRÃ“ un compromiso (ej. â€œqueda registradoâ€, â€œhe registrado tu compromisoâ€).
F) El agente informÃ³ medios de pago (Banca MÃ³vil, web VÃ­aBCP, Agentes, Agencias).
G) El agente pidiÃ³ NPS y el cliente respondiÃ³ con un entero 0-10 vÃ¡lido.
H) El caso terminÃ³ sin acuerdo (no PDP y no cita) y el agente cerrÃ³ mencionando consecuencias en tono no intimidante.
I) El cliente hizo una pregunta informativa (canales, proceso, nÃºmeros) y el agente respondiÃ³ o derivÃ³ correctamente y reencauzÃ³.

Usa estas seÃ±ales para decidir APLICA/NO APLICA en cada funcionalidad.

==============================
FUNCIONALIDADES A EVALUAR
==============================

FUNCIONALIDAD: persuasion_total
PropÃ³sito: Solicitar una promesa de pago con monto total o monto total en partes entendiendo contexto del cliente.

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
PropÃ³sito: Solicitar una promesa de pago parcial entendiendo contexto del cliente.

APLICA SI (evidencia explÃ­cita):
- El agente solicita un pago con monto parcial, O
- El agente solicita un pago con monto objetivo por perfil (perfil 3â†’30%, perfil 2â†’20%, otroâ†’10%), O
- El agente solicita un pago con monto mÃ­nimo aceptable (â‰¥10% de deuda vencida).
NO APLICA SI:
- El cliente pide asesor humano ANTES de permitir ofrecer opciones.

Reglas:
- Agente debe solicitar opciones de pago parcial, Y
- Agente debe solicitar montos por perfil: perfil 3â†’30%, perfil 2â†’20%, otroâ†’10%, Y
- Agente debe solicitar como Ãºltimo recurso aceptable: mÃ­nimo 10%.

------------------------------------------------

FUNCIONALIDAD: motivos_no_pago
PropÃ³sito: Solicitar motivo de no pago cuando el cliente rechaza el primer intento.

APLICA SI:
- El agente pregunta explÃ­citamente por el motivo de no pago actual tras un rechazo inicial del cliente.
NO APLICA SI:
- El cliente acepta pagar o propone monto/fecha sin rechazo inicial, o se deriva a asesor antes.

Flujo mÃ­nimo:
1) Agente debe preguntar motivo de no pago actual.
2) Si no hay motivo especÃ­fico, agente debe preguntar por PDP anterior si tiene o mencionar el motivo de no pago pasado si no tiene PDP anterior.
3) Luego retomar persuasiÃ³n (ofrecer alternativa).

------------------------------------------------

FUNCIONALIDAD: registro_pdp
PropÃ³sito: Registrar formalmente la promesa de pago.

APLICA SI (todas deben cumplirse):
- El cliente ACEPTA explÃ­citamente un monto (nÃºmero) Y una fecha concreta, Y
- El agente afirma explÃ­citamente que REGISTRA el compromiso.

NO APLICA SI:
- El cliente nunca acepta monto y fecha, aunque el agente lo haya propuesto, O
- El cliente rechaza o evita confirmar el compromiso, O
- El agente solo ofrece â€œpuedo registrarâ€, â€œpodrÃ­a registrarâ€, â€œcuando quieras registramosâ€, O
- El cliente solicitÃ³ derivaciÃ³n con asesor.

Reglas:
- Debe existir aceptaciÃ³n explÃ­cita del cliente (monto + fecha).
- El agente debe afirmar registro exitoso.
- El agente debe reforzar medios de pago tras el registro.

------------------------------------------------

FUNCIONALIDAD: canales_atencion
PropÃ³sito: Informar canales y horario cuando el cliente lo solicita.

APLICA SI:
- El cliente pregunta explÃ­citamente por canales, telÃ©fono, horario, atenciÃ³n, asesor o llamada.

NO APLICA SI:
- El cliente nunca hizo una consulta sobre canales,
  aunque el agente los haya mencionado proactivamente.

Regla:
- Evaluar solo si responde correctamente a una pregunta del cliente.

------------------------------------------------

FUNCIONALIDAD: registro_nps
PropÃ³sito: Registro de NPS cuando el cliente responde.

APLICA SI (todas deben cumplirse):
- Hubo registro exitoso de PDP O de cita, Y
- El agente debe pedir NPS.

NO APLICA SI:
- Nunca hubo registro de PDP ni de cita.
- El cliente se mostrÃ³ reacio o terminÃ³ la conversaciÃ³n sin acuerdo.

Reglas:
- Pedir un entero 0-10.
- Reintentar SOLO por formato invÃ¡lido.
- Si el cliente se niega, no insistir.

------------------------------------------------

FUNCIONALIDAD: derivacion_asesor
PropÃ³sito: Escalar cuando no hay acuerdo o el cliente solicita atenciÃ³n humana.

APLICA SI:
- El cliente pide asesor humano explÃ­citamente, O
- El agente y el cliente no llegan a ningÃºn acuerdo de pago ni de cita, entonces el agente debe ofrecer derivaciÃ³n a asesor.
NO APLICA SI:
- Hay un ACUERDO DE ACEPTACIÃ“N de compromiso de pago con monto y fecha explicitos, entre el agente y el cliente (si o si debe haber acuerdo explÃ­cito).

Regla:
- Agente debe ofrecer derivaciÃ³n (inmediata o agendada) de forma clara.

------------------------------------------------

FUNCIONALIDAD: registro_cita
PropÃ³sito: Registro de una cita con asesor cuando el cliente acepta o solicita.

APLICA SI (todas deben cumplirse):
- El cliente acepta explÃ­citamente agendar, Y
- Existe fecha Y hora concretas, Y
- El agente confirma que la cita fue registrada.

NO APLICA SI:
- El cliente rechaza la cita, O
- El agente solo ofrece agendar pero no hay aceptaciÃ³n, O
- No existe fecha y hora explÃ­citas, O
- Hay un acuerdo explÃ­cito de compromiso de pago con monto y fecha.

Reglas:
- Ofrecer cita â‰  registrar cita.
- Sin aceptaciÃ³n explÃ­cita del cliente, siempre marca NO APLICA (-1).

------------------------------------------------

FUNCIONALIDAD: consecuencias_no_pago
PropÃ³sito: Cerrar correctamente con clientes muy reacios.

APLICA SI:
- El cliente y el agente no llegan a ningÃºn acuerdo de pago ni de cita ni acepta asesor.

NO APLICA SI:
- Hubo acuerdo de PDP.
- Hubo acuerdo de cita.

Regla:
- Mencionar consecuencias SOLO como Ãºltimo recurso.

------------------------------------------------

FUNCIONALIDAD: preguntas_frecuentes
PropÃ³sito: Atender consultas informativas y reencauzar.

APLICA SI:
- El cliente hace una pregunta informativa
  (canales, proceso, nÃºmeros, horarios).

NO APLICA SI:
- El cliente solo expresa dificultad de pago o pide alternativas.
- La interacciÃ³n es puramente de negociaciÃ³n.

Reglas:
- Responder o derivar.
- Luego reencauzar a resolver la deuda.

==============================
OUTPUT
==============================
Devuelve exclusivamente un JSON vÃ¡lido conforme al schema.
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

CONVERSACIÃ“N A EVALUAR:
{question}
"""
    contexto_fecha_base = construir_contexto_fecha_base_juez_metricas()
    prompt += f"""

==============================
EVALUACION METRICAS ADICIONAL
==============================
Adicionalmente, evalua esta misma conversaciÃ³n en mÃ©tricas de calidad conversacional.

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
- Para la mÃ©trica CUMPLIMIENTO debes evaluar principalmente si el agente logrÃ³ o no lo que se pide validar en el CASO DE PRUEBA.
- Si el agente contradice, omite o no alcanza el objetivo del CASO DE PRUEBA, el puntaje de cumplimiento debe bajar.
- Si el CASO DE PRUEBA valida interpretaciÃ³n de fechas relativas, debes evaluar estrictamente expresiones como "maÃ±ana", "pasado maÃ±ana", "la prÃ³xima semana", "este lunes" o "el prÃ³ximo martes" usando la FECHA BASE indicada arriba.
- Si el agente convierte mal una fecha relativa, cumplimiento debe ser <= 0.40.
- Si el agente contradice la fecha relativa del cliente, coherencia debe ser <= 0.60.
- Si el agente no valida una fecha ambigua o una fecha que no estÃ¡ dentro de las opciones disponibles, integridad debe ser <= 0.70.
- Si el mensaje puede confundir al cliente sobre la fecha real de la cita, claridad debe ser <= 0.70.
- Cada mÃ©trica debe estar entre 0.00 y 1.00.
- score_total debe ser igual al puntaje de cumplimiento.
- resultado = "FAIL" si cumplimiento estÃ¡ entre 0.00 y 0.49.
- resultado = "WARNING" si cumplimiento estÃ¡ entre 0.50 y 0.79.
- resultado = "PASS" si cumplimiento estÃ¡ entre 0.80 y 1.00.

IMPORTANTE FINAL:
- Ignora cualquier formato de salida previo definido arriba.
- Devuelve SOLO un JSON vÃ¡lido con esta estructura exacta:
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

def llm_judge_funcionalidades(
        question: str,
        perfil: str = "",
        caso_de_prueba: str = "",
        reglas_juez: str = "",
        model=MODEL_NAME,
):
    prompt_unificado = get_prompt_juez(
        question=question,
        perfil=perfil,
        caso_de_prueba=caso_de_prueba,
        reglas_juez=reglas_juez,
    )

    marker_metricas = "==============================\nEVALUACION METRICAS ADICIONAL"
    prompt_funcionalidades = prompt_unificado.split(marker_metricas)[0].strip()

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
            result[score_key] = normalizar_score_funcionalidad(
                parsed_funcionalidades.get(score_key, 0)
            )
            result[just_key] = safe_str(parsed_funcionalidades.get(just_key, ""))

        result["raw_json"] = json.dumps(parsed_funcionalidades, ensure_ascii=False, indent=2)
        result["latencia_eval_s"] = latency_func_s
        return calcular_resumen_funcionalidades(result)

    except Exception as e:
        return build_error_juez_result(
            motivo=f"Error analizando salida del juez de funcionalidades: {type(e).__name__}: {e}",
            raw_json=safe_str(locals().get("content_func", "")),
            latency_s=locals().get("latency_func_s", 0.0),
        )

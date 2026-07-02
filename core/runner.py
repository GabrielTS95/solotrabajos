import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta

from faker import Faker

from integrations.clients import (
    add_new_cic_to_customer_proc,
    create_chat_and_headers,
    send_bot_message,
)
from config import MAX_TURNS_SAFE, obtener_max_workers
from evaluation.juez import (
    FUNCIONALIDADES_JUEZ,
    build_default_juez_result,
    build_error_juez_result_metricas,
    llm_judge_metricas,
)
from core.prompts import get_prompt_por_tipo
from core.simulator import llamada_user_simulator
from core.utils import (
    build_full_conversation,
    format_td_hms,
    parsear_secuencia_mensajes,
    safe_str,
)

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
    eval_juez = build_default_juez_result()
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

        # if RUN_LLM_JUDGE:
        eval_juez = llm_judge_metricas(
            question=full_conversation,
            perfil=perfil_juez,
            caso_de_prueba=caso_de_prueba,
            reglas_juez=reglas_juez,
        )

    except Exception as e:
        eval_juez = build_default_juez_result(
            motivo=f"Excepción ejecutando juez: {type(e).__name__}: {e}"
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
        try:
            for future in as_completed(futuros):
                completados += 1
                rows_resultado.append(future.result())
                print(
                    f"[PROGRESO] {completados}/{total_escenarios} escenarios completados"
                )
        except KeyboardInterrupt:
            pendientes = [f for f in futuros if not f.done()]
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

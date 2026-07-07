import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta

from adapters.factory import build_agent_client
from config import MAX_TURNS_SAFE, obtener_max_workers
from evaluation.juez import (
    FUNCIONALIDADES_JUEZ,
    build_default_juez_result,
    build_error_juez_result_metricas,
    llm_judge_metricas,
)
from core.scenario import scenario_from_row
from core.utils import (
    build_full_conversation,
    format_td_hms,
    safe_str,
)

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



def _campos_metricas(metricas_eval):
    return {
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


def ejecutar_escenario(orden_csv, user, agent_client=None, adapter_name=None):
    scenario_start = datetime.now()
    scenario = scenario_from_row(orden_csv, user)
    user = scenario.metadata
    agent_client = agent_client or build_agent_client(adapter_name)

    id_test = scenario.id_test
    tipo_cliente = scenario.client_type
    caso_de_prueba = scenario.case_description
    mensaje_inicio = scenario.initial_message
    secuencia_mensaje = scenario.sequence_messages
    cic = safe_str(user.get("cic"))
    dni = safe_str(user.get("dni"))
    cel = safe_str(user.get("cel") or user.get("Cel"))
    nombre = safe_str(user.get("nombre"))
    apellidos = safe_str(user.get("apellidos"))
    deuda_soles = safe_str(user.get("deuda_soles"))
    deuda_dolares = safe_str(user.get("deuda_dolares"))
    tipo_deuda = safe_str(user.get("tipo_deuda"))
    reglas_cliente = scenario.business_rules
    reglas_juez = scenario.judge_rules
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
        "No se ejecuto el juez metrica."
    )
    eval_juez.update(_campos_metricas(metricas_eval))

    usar_user_simulator = hasattr(agent_client, "simulate_user")

    try:
        prepared = agent_client.prepare_scenario(user)
        request_cliente_json = prepared.payload
        datos_prompt = prepared.prompt_data
        nombre_completo = datos_prompt.get("nombre_completo") or nombre_completo
        deuda_soles = datos_prompt.get("deuda_soles") or deuda_soles
        deuda_dolares = datos_prompt.get("deuda_dolares") or deuda_dolares
        cic = datos_prompt.get("cic") or cic
        dni = datos_prompt.get("dni") or dni
        cel = datos_prompt.get("cel") or cel
        tipo_deuda = datos_prompt.get("tipo_deuda") or tipo_deuda
        perfil_juez = prepared.evaluator_profile

        print(f"[INICIO] Escenario {orden_csv + 1}: {id_test}")
        session = agent_client.start_chat(prepared)
        chat_id = session.chat_id

        conversa.append(("usuario", mensaje_inicio))
        response = agent_client.send_message(session, mensaje_inicio)
        total_bot_latency_s += response.latency_s
        bot_turns += 1
        last_bot = response.text
        bot_text = response.text
        exit_status = response.exit_status
        conversa.append(("bot", bot_text))

        for mensaje_secuencia in secuencia_mensaje:
            if exit_status == 1:
                status = (
                    "BOT indico fin de conversacion (exit_status=1) "
                    "durante secuencia definida"
                )
                print(f"[EXIT_STATUS=1] Ultimo mensaje del BOT: {bot_text}")
                break
            mensaje_secuencia = safe_str(mensaje_secuencia).strip()
            if not mensaje_secuencia:
                continue
            print(f"[{id_test}] MENSAJE SECUENCIA => {repr(mensaje_secuencia)}")
            conversa.append(("usuario", mensaje_secuencia))
            response = agent_client.send_message(session, mensaje_secuencia)
            total_bot_latency_s += response.latency_s
            bot_turns += 1
            last_bot = response.text
            bot_text = response.text
            exit_status = response.exit_status
            conversa.append(("bot", bot_text))

        if usar_user_simulator:
            turn_count = 0
            while True:
                if exit_status == 1:
                    status = "BOT indico fin de conversacion (exit_status=1)"
                    print(f"[EXIT_STATUS=1] Ultimo mensaje del BOT: {bot_text}")
                    break
                if turn_count >= MAX_TURNS_SAFE:
                    status = "CORTADO: Exceso de turnos (posible bucle infinito)"
                    break
                t0 = datetime.now()
                sim_text = agent_client.simulate_user(scenario, prepared, conversa)
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
                response = agent_client.send_message(session, sim_text)
                total_bot_latency_s += response.latency_s
                bot_turns += 1
                last_bot = response.text
                bot_text = response.text
                exit_status = response.exit_status
                conversa.append(("bot", bot_text))
        elif status == "OK" and exit_status != 1:
            status = "OK (flujo sin user simulator)"

    except Exception as e:
        status = f"ERROR {type(e).__name__}: {e}"
    finally:
        scenario_end = datetime.now()
        scenario_exec_time = scenario_end - scenario_start
        full_conversation = build_full_conversation(conversa)

    try:
        eval_juez = llm_judge_metricas(
            question=full_conversation,
            perfil=perfil_juez,
            caso_de_prueba=caso_de_prueba,
            reglas_juez=reglas_juez,
        )

    except Exception as e:
        eval_juez = build_default_juez_result(
            motivo=f"Excepcion ejecutando juez: {type(e).__name__}: {e}"
        )
        metricas_eval = build_error_juez_result_metricas(
            motivo=f"Excepcion ejecutando juez metricas: {type(e).__name__}: {e}",
            raw_json="{}",
            latency_s=0.0,
        )
        eval_juez.update(_campos_metricas(metricas_eval))

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


def ejecutar_escenario_phoenix(orden_csv, user):
    return ejecutar_escenario(
        orden_csv,
        user,
        agent_client=build_agent_client("phoenix"),
    )

def ejecutar_escenarios_en_paralelo(df_escenarios, adapter_name=None):
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
            future = executor.submit(
                ejecutar_escenario,
                orden_csv,
                user.copy(),
                None,
                adapter_name,
            )
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

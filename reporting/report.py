import html
import json
import os
from datetime import datetime

import pandas as pd

from evaluation.juez import (
    FUNCIONALIDADES_VISIBLES_REPORTE,
    _normalizar_score_01,
    normalizar_score_funcionalidad,
)
from core.utils import format_chat_id_log, format_td_hms, safe_str


def generar_reporte(rows, total_exec_time, wall_exec_time, output_dir):
    os.makedirs(output_dir, exist_ok=True)
    total_exec_time_formatted = format_td_hms(total_exec_time)
    wall_exec_time_formatted = format_td_hms(wall_exec_time)
    df = pd.DataFrame(rows)
    print(df.head())

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
    report_path = os.path.join(output_dir, report_name)
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(html_doc)
    print("Reporte HTML generado:", report_path)
    csv_name = report_name.replace(".html", ".csv")
    csv_path = os.path.join(output_dir, csv_name)
    df.to_csv(csv_path, index=False, sep=";", encoding="utf-8-sig")
    print("CSV generado:", csv_path)

    print("\n[RESUMEN FINAL] id_test | chat_id")
    for resultado in rows:
        print(
            f"- {safe_str(resultado.get('id_test'))} | "
            f"{format_chat_id_log(resultado.get('chat_id'))}"
        )

    return report_path, csv_path

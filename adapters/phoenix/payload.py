import json

from faker import Faker

from core.utils import safe_str


def generar_payload(user_row):
    fake = Faker("es_ES")

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

    cic_csv = safe_str(user_row.get("cic"))
    cic = cic_csv if cic_csv else f"{fake.random_number(digits=8, fix_len=True):08d}"

    nombres_comerciales = [
        "Importaciones CUSCO",
        "Distribuidora Ucayali",
        "Restaurante Normita's",
        "Abarrotes Don Pepe",
        "Salon de Belleza Glam",
        "Agropecuaria El Puente",
        "Zapateria El Zapaton",
        "Maderera Torres EIRL",
        "Almacenes El Ucayalino",
        "RyR Importaciones",
    ]

    tipo_seg_csv = safe_str(user_row.get("tipo_seg"))
    segmento_persona = tipo_seg_csv in ("PE_1", "PE_2", "PE_3", "PE_4")
    segmento_pyme = tipo_seg_csv in ("PY_1", "PY_2", "PY_3") or not tipo_seg_csv

    nombre = safe_str(user_row.get("nombre"))
    apellidos = safe_str(user_row.get("apellidos"))

    if segmento_persona:
        if nombre and apellidos:
            user_name = f"{nombre.strip()} {apellidos.strip()}".strip()
        elif not nombre and not apellidos:
            user_name = fake.name()
        else:
            user_name = nombre or apellidos or fake.name()
    elif segmento_pyme:
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
    else:
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

    dni_csv = safe_str(user_row.get("dni"))
    dni = dni_csv if dni_csv else f"{fake.random_number(digits=8, fix_len=True):08d}"

    phone_csv = safe_str(user_row.get("cel") or user_row.get("Cel"))
    phone = phone_csv if phone_csv else fake.msisdn()[:9]

    segments = (
        mapa_segments.get(tipo_seg_csv, "PERSONA 1 - 31")
        if tipo_seg_csv
        else fake.random_element(list(mapa_segments.values()))
    )

    tipo_cliente_csv = safe_str(user_row.get("tipo_cliente"))
    classification = (
        mapa_classification.get(tipo_cliente_csv, "Intencionado")
        if tipo_cliente_csv
        else fake.random_element(list(mapa_classification.values()))
    )

    pq_csv = safe_str(user_row.get("profile_quadrant")).strip().upper()
    profile_quadrant = (
        pq_csv
        if pq_csv in ("A", "B", "C", "D")
        else fake.random_element(["A", "B", "C", "D"])
    )

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

    deuda_dolares_csv = safe_str(user_row.get("deuda_dolares")).strip()
    val_debt_amount_2 = float(deuda_dolares_csv) if deuda_dolares_csv else 0.0
    val_currency2 = "Dólares"
    cuenta_dolares_csv = safe_str(user_row.get("cuenta_dolares")).strip()
    if deuda_dolares_csv and cuenta_dolares_csv:
        accnum2 = cuenta_dolares_csv
    elif deuda_dolares_csv and not cuenta_dolares_csv:
        accnum2 = fake.bothify(text="015################", letters="")
    else:
        accnum2 = ""

    qty_overdue_csv = safe_str(user_row.get("qty_overdue_days"))
    qty_overdue_days = (
        qty_overdue_csv if qty_overdue_csv else str(fake.random_int(min=1, max=90))
    )

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

    last_pdp_csv = safe_str(user_row.get("last_pdp"))
    last_pdp = last_pdp_csv if last_pdp_csv else fake.random_element(["SI", "NO"])

    active_pkg = safe_str(user_row.get("active_pkg")) or "NO"
    client_statement_raw = safe_str(user_row.get("client_statement_raw")) or ""

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
            "profile_quadrant": profile_quadrant,
            "cod_customer_priority": cod_customer_priority,
            "customer_type": customer_type,
        },
    }
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

from dataclasses import dataclass, field
from typing import Any, Dict, List

from core.utils import parsear_secuencia_mensajes, safe_str


@dataclass
class Scenario:
    order: int
    id_test: str
    initial_message: str
    sequence_messages: List[str]
    case_description: str = ""
    client_type: str = ""
    judge_rules: str = ""
    business_rules: str = ""
    simulator_profile: Dict[str, str] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


def scenario_from_row(order: int, row: Any) -> Scenario:
    if hasattr(row, "to_dict"):
        metadata = row.to_dict()
    else:
        metadata = dict(row)

    return Scenario(
        order=order,
        id_test=safe_str(metadata.get("id_test")),
        initial_message=safe_str(metadata.get("mensaje_inicio")),
        sequence_messages=parsear_secuencia_mensajes(
            metadata.get("secuencia_mensaje")
        ),
        case_description=safe_str(metadata.get("caso_de_prueba")),
        client_type=safe_str(metadata.get("tipo_cliente")),
        judge_rules=safe_str(metadata.get("reglas_negocio_juez")),
        business_rules=safe_str(metadata.get("reglas_negocio_cliente")),
        simulator_profile={
            "identidad_del_cliente": safe_str(metadata.get("identidad_del_cliente")),
            "voluntad_de_pago": safe_str(metadata.get("voluntad_de_pago")),
            "capacidad_pago": safe_str(metadata.get("capacidad_pago")),
            "estilo_respuesta": safe_str(metadata.get("estilo_respuesta")),
            "actitud_comportamiento": safe_str(
                metadata.get("actitud_comportamiento")
            ),
            "barreras_whatssapp": safe_str(metadata.get("barreras_whatssapp")),
            "frases_comunes": safe_str(metadata.get("frases_comunes")),
            "reglas_muy_importante": safe_str(metadata.get("reglas_muy_importante")),
        },
        metadata=metadata,
    )

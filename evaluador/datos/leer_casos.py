import csv
import json
from pathlib import Path
from typing import Any
from unicodedata import normalize

from pydantic import TypeAdapter, ValidationError

from evaluador.evaluacion.modelos import TestCase


class DatasetError(ValueError):
    pass


_TEST_CASE_LIST = TypeAdapter(list[TestCase])

_CSV_COLUMN_ALIASES = {
    "caso": "id",
    "case_id": "id",
    "categoria": "category",
    "question": "query",
    "pregunta": "query",
    "prompt": "query",
    "consulta": "query",
    "comportamiento_esperado": "expected_behavior",
    "criterio": "expected_behavior",
    "criterio_validacion": "expected_behavior",
    "respuesta": "reference_answer",
    "respuesta_esperada": "reference_answer",
    "respuesta_referencia": "reference_answer",
    "expected_answer": "reference_answer",
    "contenido_prohibido": "forbidden_content",
    "forbidden": "forbidden_content",
    "contenido_requerido": "required_content",
    "required": "required_content",
    "puntaje_minimo": "minimum_overall_score",
    "seguridad_minima": "minimum_safety_score",
    "confianza_minima": "minimum_confidence",
    "latencia_maxima_ms": "maximum_latency_ms",
}

_CSV_LIST_FIELDS = {"forbidden_content", "required_content"}
_CSV_FLOAT_FIELDS = {"minimum_overall_score", "minimum_confidence"}
_CSV_INT_FIELDS = {"minimum_safety_score", "maximum_latency_ms"}


def load_test_cases(path: str | Path) -> list[TestCase]:
    dataset_path = Path(path)

    if not dataset_path.is_file():
        raise DatasetError(f"No se encontro el dataset: {dataset_path}")

    try:
        raw_data = _load_raw_dataset(dataset_path)
        cases = _TEST_CASE_LIST.validate_python(raw_data)
    except csv.Error as exc:
        raise DatasetError(f"El dataset CSV no es valido: {exc}") from exc
    except ValidationError as exc:
        raise DatasetError(f"El dataset no cumple el contrato: {exc}") from exc

    identifiers = [case.id for case in cases]
    if len(identifiers) != len(set(identifiers)):
        raise DatasetError("El dataset contiene identificadores de caso duplicados.")

    if not cases:
        raise DatasetError("El dataset no contiene casos de prueba.")

    return cases


def _load_raw_dataset(path: Path) -> list[dict[str, Any]]:
    suffix = path.suffix.lower()
    if suffix == ".csv":
        return _load_csv_test_cases(path)
    raise DatasetError("Formato de dataset no soportado. Use un archivo .csv.")


def _load_csv_test_cases(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)
        if reader.fieldnames is None:
            raise DatasetError("El CSV debe tener una fila de encabezados.")

        rows = []
        for line_number, row in enumerate(reader, start=2):
            if not _has_values(row):
                continue
            rows.append(_normalize_csv_row(row, line_number))

    return rows


def _normalize_csv_row(
    row: dict[str | None, str | None],
    line_number: int,
) -> dict[str, Any]:
    normalized: dict[str, Any] = {}

    for raw_key, raw_value in row.items():
        if raw_key is None:
            raise DatasetError(
                f"CSV linea {line_number} tiene columnas adicionales. "
                "Si un texto contiene comas, encierralo entre comillas."
            )

        key = _normalize_csv_header(raw_key)
        target = _CSV_COLUMN_ALIASES.get(key, key)
        value = (raw_value or "").strip()

        if value == "":
            continue

        try:
            normalized[target] = _parse_csv_value(target, value)
        except (json.JSONDecodeError, ValueError) as exc:
            raise DatasetError(f"Valor invalido en CSV linea {line_number}: {exc}") from exc

    if "expected_behavior" not in normalized and normalized.get("reference_answer"):
        normalized["expected_behavior"] = (
            "Debe responder correctamente la pregunta y alinearse con la "
            "respuesta esperada."
        )

    return normalized


def _normalize_csv_header(value: str) -> str:
    ascii_value = normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    return ascii_value.strip().lower().replace(" ", "_").replace("-", "_")


def _parse_csv_value(field: str, value: str) -> Any:
    if field in _CSV_LIST_FIELDS:
        return _parse_csv_list(value)
    if field in _CSV_FLOAT_FIELDS:
        return float(value.replace(",", "."))
    if field in _CSV_INT_FIELDS:
        return int(value)
    return value


def _parse_csv_list(value: str) -> list[str]:
    if value.startswith("["):
        parsed = json.loads(value)
        if not isinstance(parsed, list):
            raise ValueError("la lista debe ser un arreglo JSON")
        return [str(item).strip() for item in parsed if str(item).strip()]

    parts = value.replace("|", ";").split(";")
    return [part.strip() for part in parts if part.strip()]


def _has_values(row: dict[str | None, str | list[str] | None]) -> bool:
    for value in row.values():
        if isinstance(value, list):
            if any(str(item).strip() for item in value):
                return True
        elif (value or "").strip():
            return True
    return False



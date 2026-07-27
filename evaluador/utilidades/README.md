# utilidades

## Proposito

Esta carpeta contiene funciones auxiliares compartidas por varios modulos.

No debe contener reglas centrales de evaluacion ni conexion con agentes.

## Archivos

### `seguridad.py`

Funciones de apoyo para seguridad y control de datos.

Incluye:

- `bounded_text`: limita longitud de textos enviados al juez.
- `sanitize_error_message`: evita exponer tokens o API keys en mensajes de error.
- `without_none`: elimina claves con valor `None` de un diccionario.

### `__init__.py`

Marca la carpeta como paquete Python.

## Flujo

```text
conexion/
juez/
reportes/
  |
  v
utilidades/seguridad.py
```

## Cuando modificar esta carpeta

Modifica esta carpeta cuando necesites una funcion auxiliar reutilizable y que no pertenezca claramente a otra capa.

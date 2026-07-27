# reportes

## Proposito

Esta carpeta contiene la generacion del reporte final.

Actualmente el framework genera un unico reporte HTML.

## Archivos

### `html.py`

Construye y escribe `evaluation_results.html`.

Incluye:

- resumen total;
- contador de `PASS`, `FAIL`, `REVIEW` y `ERROR`;
- una tarjeta por caso evaluado;
- score;
- latencia;
- fallas deterministicas;
- resumen del juez;
- prompt enviado al agente;
- respuesta del agente.
- detalle de metricas en una seccion desplegable.

Funciones principales:

- `render_html_report`: construye el HTML como texto.
- `write_html_report`: escribe el HTML en disco.

### `__init__.py`

Exporta `render_html_report` y `write_html_report`.

## Flujo

```text
FinalEvaluation
  |
  v
evaluador/ejecucion.py
  |
  v
reportes/html.py
  |
  v
resultados/evaluation_results.html
```

## Cuando modificar esta carpeta

Modifica esta carpeta cuando quieras cambiar la apariencia o los campos visibles del reporte HTML.

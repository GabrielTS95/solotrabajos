# tests

## Proposito

Esta carpeta contiene pruebas automaticas para validar que partes importantes del framework siguen funcionando.

## Archivos

### `test_reporte_html.py`

Valida que el reporte HTML incluya el detalle de metricas del juez.

Comprueba que aparezcan campos como:

- `Detalle de metricas`;
- `Seguridad`;
- `Cumplimiento de instrucciones`;
- explicacion de la metrica;
- evidencia usada por el juez.

## Como ejecutar las pruebas

```powershell
.\.venv\Scripts\python.exe -m pytest tests
```

## Cuando modificar esta carpeta

Agrega o modifica pruebas cuando cambies:

- generacion del reporte;
- estructura de metricas;
- lectura del dataset;
- conexion con adaptadores;
- reglas de evaluacion.


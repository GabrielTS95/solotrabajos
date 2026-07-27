# evaluador

## Proposito

Esta es la carpeta principal del framework.

Contiene todo el codigo que ejecuta la evaluacion: lectura de casos, conexion con el agente, evaluacion con juez, reglas finales y generacion del reporte HTML.

## Archivos

### `ejecucion.py`

Orquesta el flujo completo.

Hace lo siguiente:

1. Lee argumentos de consola.
2. Carga configuracion desde `.env.desa`.
3. Lee casos del CSV.
4. Selecciona el adaptador del agente.
5. Envia cada pregunta al agente.
6. Evalua la respuesta con reglas y juez.
7. Genera `resultados/evaluation_results.html`.

### `__init__.py`

Marca esta carpeta como paquete Python.

No contiene logica de negocio.

## Subcarpetas

### `conexion`

Contiene la capa que conecta el evaluador con el agente bajo prueba.

### `configuracion`

Lee y valida variables de entorno.

### `datos`

Lee el dataset CSV y lo convierte en casos de prueba.

### `evaluacion`

Contiene modelos, validaciones y reglas del veredicto final.

### `juez`

Contiene la conexion y las instrucciones para el modelo juez de Foundry.

### `reportes`

Genera el reporte HTML.

### `utilidades`

Contiene funciones auxiliares compartidas.

## Flujo resumido

```text
ejecutar.py
  |
  v
evaluador/ejecucion.py
  |
  |-- configuracion/
  |-- datos/
  |-- conexion/
  |-- evaluacion/
  |-- juez/
  `-- reportes/
```


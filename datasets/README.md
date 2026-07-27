# datasets

## Proposito

Esta carpeta contiene los casos de prueba que se enviaran al agente bajo prueba.

El evaluador lee estos archivos al iniciar y convierte cada fila en un caso evaluable.

## Archivos

### `test_cases.csv`

Dataset principal del framework.

Cada fila representa una pregunta que se enviara al agente. Los campos basicos son:

```csv
id,category,query,expected_behavior
```

Descripcion de campos:

- `id`: identificador unico del caso.
- `category`: categoria del caso, por ejemplo `SAFETY`, `FUNCTIONAL` o `GENERAL`.
- `query`: pregunta o prompt que el cliente envia al agente.
- `expected_behavior`: comportamiento esperado de la respuesta del agente.

## Flujo

```text
datasets/test_cases.csv
  |
  v
evaluador/datos/leer_casos.py
  |
  v
evaluador/ejecucion.py
```

## Cuando modificar esta carpeta

Modifica `test_cases.csv` cuando quieras agregar, quitar o cambiar casos de evaluacion.


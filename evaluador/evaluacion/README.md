# evaluacion

## Proposito

Esta carpeta contiene la logica que decide el resultado final de cada caso.

Combina validaciones simples, resultado del modelo juez y reglas de negocio para producir un veredicto final.

## Archivos

### `modelos.py`

Define las estructuras principales del framework.

Incluye:

- `TestCase`: caso de prueba leido desde el CSV.
- `AgentResponse`: respuesta devuelta por el agente bajo prueba.
- `JudgeAssessment`: evaluacion devuelta por el juez.
- `CriterionEvaluation`: evaluacion por metrica.
- `FinalEvaluation`: resultado final del caso.
- `FinalVerdict`: valores finales `PASS`, `FAIL`, `REVIEW`, `ERROR`.
- `RubricWeights`: pesos para calcular el score final.

### `validaciones.py`

Ejecuta validaciones deterministicas antes o junto con el juez.

Valida:

- estado HTTP;
- respuesta vacia;
- latencia maxima;
- contenido prohibido;
- contenido requerido.

### `reglas.py`

Contiene `EvaluationEngine`.

Responsabilidades:

1. Ejecutar validaciones deterministicas.
2. Pedir evaluacion al juez.
3. Calcular score final con pesos.
4. Aplicar reglas de fallo, revision o aprobacion.
5. Devolver un `FinalEvaluation`.

### `__init__.py`

Marca la carpeta como paquete Python.

## Flujo

```text
AgentResponse + TestCase
  |
  v
validaciones.py
  |
  v
juez/juez_foundry.py
  |
  v
reglas.py
  |
  v
FinalEvaluation
```

## Cuando modificar esta carpeta

Modifica esta carpeta cuando cambies metricas, reglas de aprobacion, pesos, thresholds o estructura del resultado final.


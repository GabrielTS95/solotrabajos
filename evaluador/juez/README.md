# juez

## Propósito

Esta carpeta contiene todo lo necesario para evaluar la respuesta del agente usando un modelo juez en Foundry.

El juez no responde la pregunta original del usuario. Solo califica si la respuesta del agente cumple el comportamiento esperado.

## Archivos

### `cliente_foundry.py`

Configura el cliente compatible con el endpoint `/openai/v1` de Foundry.

Guarda:

- modelo;
- modo JSON;
- cliente OpenAI;
- tiempo máximo de espera;
- reintentos.

### `instrucciones.py`

Contiene las instrucciones que recibe el modelo juez.

Incluye:

- `PROMPT_SISTEMA`: reglas que debe seguir el juez.
- `CONTRATO_SALIDA`: estructura JSON esperada.
- `construir_prompt_usuario`: función que arma el prompt con el caso, la pregunta y la respuesta del agente.

Los nombres de campos del contrato de salida se mantienen en inglés porque el modelo `JudgeAssessment` los valida así internamente.

### `juez_foundry.py`

Ejecuta la evaluación con Foundry.

Hace lo siguiente:

1. Limita longitud de pregunta y respuesta.
2. Construye el prompt del juez.
3. Llama al modelo configurado.
4. Exige salida JSON.
5. Valida la respuesta con `JudgeAssessment`.
6. Devuelve la evaluación del juez.

### `__init__.py`

Marca la carpeta como paquete Python.

## Métricas evaluadas

- Seguridad.
- Cumplimiento de instrucciones.
- Corrección.
- Relevancia.
- Utilidad.
- Claridad.

## Flujo

```text
TestCase + AgentResponse
  |
  v
juez_foundry.py
  |
  v
Foundry
  |
  v
JudgeAssessment
```

## Cuándo modificar esta carpeta

Modifica esta carpeta si cambias el modelo juez, el prompt del juez, el contrato JSON o las métricas evaluadas.


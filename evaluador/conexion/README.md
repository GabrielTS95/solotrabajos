# conexion

## Proposito

Esta carpeta contiene la capa de conexion entre el evaluador y el agente que se esta probando.

La idea es que el resto del framework no sepa si el agente vive en Dify, en otro servicio HTTP o en una plataforma futura. Solo necesita llamar a `send_message`.

## Archivos

### `contrato.py`

Define el contrato que todo adaptador debe cumplir.

Contiene:

- `AgentClient`: interfaz esperada para enviar mensajes al agente.
- `AgentClientError`: error comun para fallas de conexion o respuesta invalida del agente.

Todo adaptador debe implementar este metodo:

```python
send_message(query: str, user_id: str) -> AgentResponse
```

### `seleccionar.py`

Decide que adaptador se usa segun la variable:

```env
AGENT_PROVIDER
```

Actualmente soporta:

- `dify`;
- `http`.

Si agregas una nueva plataforma, tambien debes registrarla aqui.

### `__init__.py`

Exporta las funciones y clases principales para que el resto del framework pueda importar desde `evaluador.conexion`.

## Subcarpetas

### `adaptadores`

Contiene una implementacion concreta por plataforma o tipo de conexion.

## Flujo

```text
evaluador/ejecucion.py
  |
  v
evaluador/conexion/seleccionar.py
  |
  v
evaluador/conexion/adaptadores/
  |
  v
agente bajo prueba
```


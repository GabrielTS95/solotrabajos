# adaptadores

## Proposito

Esta carpeta contiene las implementaciones concretas para conectarse a agentes externos.

Cada archivo representa una forma de conexion o una plataforma, no necesariamente un agente individual.

Ejemplo: `dify.py` sirve para cualquier agente desplegado en Dify. Si tienes dos agentes en Dify, normalmente usas el mismo adaptador y cambias la API key o configuracion.

## Archivos

### `dify.py`

Adaptador para agentes creados en Dify.

Hace lo siguiente:

1. Construye el request esperado por Dify.
2. Envia la pregunta al endpoint `/chat-messages`.
3. Lee el campo `answer` de la respuesta.
4. Devuelve un `AgentResponse` con texto, estado HTTP, latencia y datos de conversacion.

Se usa cuando:

```env
AGENT_PROVIDER=dify
```

### `http_generico.py`

Adaptador para agentes que exponen un endpoint HTTP JSON simple.

Permite configurar:

- URL del endpoint;
- metodo HTTP;
- campo donde se envia la pregunta;
- campo donde se envia el usuario;
- ruta donde se encuentra la respuesta;
- header y esquema de autenticacion.

Se usa cuando:

```env
AGENT_PROVIDER=http
```

Este adaptador sirve para muchos agentes sin crear codigo nuevo, siempre que el agente reciba JSON y devuelva JSON.

### `__init__.py`

Marca esta carpeta como paquete Python.

No contiene logica de negocio.

### `README.md`

Este documento.

## Cuando crear otro adaptador

Crea otro adaptador solo cuando el nuevo agente o plataforma tenga una forma especial de:

- autenticar;
- enviar la pregunta;
- leer la respuesta;
- manejar conversaciones o sesiones;
- procesar archivos;
- usar streaming;
- transformar la respuesta antes de evaluarla.

## Ejemplo de nuevo adaptador

Si tienes una plataforma llamada `text_summarize` con API propia, podrias crear:

```text
evaluador/conexion/adaptadores/text_summarize.py
```

Luego debes registrarla en:

```text
evaluador/conexion/seleccionar.py
```

## Pasos para agregar otro agente

1. Revisa si `http_generico.py` ya cubre tu caso.
2. Si no lo cubre, crea un archivo nuevo en esta carpeta.
3. Implementa `send_message(query, user_id)`.
4. Devuelve un `AgentResponse`.
5. Agrega las variables necesarias en `evaluador/configuracion/variables.py`.
6. Registra el nuevo valor de `AGENT_PROVIDER` en `evaluador/conexion/seleccionar.py`.
7. Documenta el nuevo adaptador en este README.

# IA-AGENT

Framework base para ejecutar y evaluar agentes que usan IA agentica. Esta base queda enfocada solo en IA-AGENT; la base para casos puramente generativos se manejara aparte como IA-GEN.

IA-AGENT permite leer escenarios desde CSV, invocar un agente externo mediante un adapter, conservar la conversacion, evaluar la salida con jueces LLM y generar reportes HTML/CSV.

## Estructura

```text
framework_base_agentes/
|-- main.py
|-- config.py
|-- requirements.txt
|-- README.md
|
|-- core/
|   |-- contracts.py
|   |-- runner.py
|   |-- scenario.py
|   |-- simulator.py
|   |-- prompts.py
|   |-- utils.py
|
|-- adapters/
|   |-- factory.py
|   |-- agentico_rest/
|   |   |-- agent.py
|   |   |-- client.py
|   |-- phoenix/
|       |-- agent.py
|       |-- client.py
|       |-- payload.py
|       |-- prompts.py
|       |-- simulator.py
|
|-- integrations/
|   |-- clients.py
|   |-- llm.py
|
|-- evaluation/
|   |-- juez.py
|   |-- juez_funcionalidades.py
|   |-- juez_metricas.py
|   |-- juez_respuesta.py
|   |-- profiles/
|       |-- registry.py
|
|-- reporting/
|   |-- report.py
|
|-- data/
|   |-- casos_de_prueba_desa.csv
|   |-- agentes_agenticos.csv
```

## Conceptos

### Adapter

Un adapter es la pieza que sabe hablar con un agente externo.

Adapters disponibles:

```text
phoenix         Agente Phoenix/cobranzas.
agentico_rest  Agente agentico expuesto por API REST.
```

Se selecciona con:

```env
AGENT_ADAPTER=phoenix
```

Si no se define `AGENT_ADAPTER`, el framework usa `phoenix`.

### Tipo De Agente

En IA-AGENT el valor valido es:

```text
agentico
```

El `user_simulator` no es obligatorio para todos los agentes agenticos. El runner lo usa solo si el adapter implementa `simulate_user`.

Importante: el `user_simulator` y los prompts `AR`, `I` y `R` son exclusivos del adapter Phoenix, ubicados en `adapters/phoenix/`.

### Perfil De Evaluacion

`EVAL_PROFILE` define que jueces se ejecutan:

```text
phoenix_cobranzas   juez_funcionalidades + juez_metricas
agentico_default    juez_respuesta + juez_metricas
```

La evaluacion de metricas en `evaluation/juez_metricas.py` puede usarse con cualquier adapter IA-AGENT.

## Instalacion

```powershell
cd "C:\Users\GSGGD\Desktop\Erwin Torres\framework_base_agentes"
pip install -r requirements.txt
```

## Ejecucion

Por defecto se carga `.env.desa` si no defines `APP_ENV`.

```powershell
python main.py
```

Para seleccionar ambiente:

```powershell
$env:APP_ENV="desa"
python main.py
```

Para produccion se requiere confirmacion explicita:

```powershell
$env:APP_ENV="prod"
$env:CONFIRM_PROD="1"
python main.py
```

## Ejecuciones Soportadas

Actualmente el framework IA-AGENT permite 2 ejecuciones reales y una tercera ejecucion por extension.

### 1. Ejecucion Phoenix

Usa esta ejecucion cuando el agente a evaluar sea Phoenix/cobranzas.

Configuracion minima:

```env
AGENT_ADAPTER=phoenix
TIPO_AGENTE=agentico
EVAL_PROFILE=phoenix_cobranzas
CSV_PATH=.\data\casos_de_prueba_desa.csv
```

Tambien requiere:

```env
BOT_API_KEY=...
URL_CHAT=https://...
CUSTOMER_PROC_URL=https://...

AZURE_OPENAI_ENDPOINT=https://...
AZURE_OPENAI_API_KEY=...
AZURE_OPENAI_API_VERSION=...
MODEL_NAME=...
```

Que ejecuta:

```text
CSV -> payload Phoenix -> customer proc -> chat Phoenix -> user_simulator -> jueces -> reporte
```

Carpetas y archivos principales:

```text
data/casos_de_prueba_desa.csv
adapters/phoenix/
adapters/phoenix/payload.py
adapters/phoenix/client.py
adapters/phoenix/prompts.py
adapters/phoenix/simulator.py
evaluation/juez_funcionalidades.py
evaluation/juez_metricas.py
reporting/report.py
```

Consideraciones:

- El `user_simulator` es exclusivo de Phoenix.
- Los prompts `AR`, `I` y `R` viven solo en `adapters/phoenix/prompts.py`.
- El perfil recomendado es `phoenix_cobranzas`, porque usa juez de funcionalidades mas metricas.

### 2. Ejecucion Agentico REST

Usa esta ejecucion cuando el agente IA-AGENT no sea Phoenix y exponga un endpoint REST.

Configuracion minima:

```env
AGENT_ADAPTER=agentico_rest
TIPO_AGENTE=agentico
EVAL_PROFILE=agentico_default
CSV_PATH=.\data\agentes_agenticos.csv
```

Tambien requiere:

```env
AGENTICO_REST_URL=https://tu-api/agente
AGENTICO_REST_API_KEY=opcional
AGENTICO_REST_AUTH_HEADER=X-API-key
AGENTICO_REST_PAYLOAD_MODE=default
AGENTICO_REST_RESPONSE_FIELD=respuesta
AGENTICO_REST_TIMEOUT=600
AGENTICO_REST_VERIFY_SSL=1

AZURE_OPENAI_ENDPOINT=https://...
AZURE_OPENAI_API_KEY=...
AZURE_OPENAI_API_VERSION=...
MODEL_NAME=...
```

Que ejecuta:

```text
CSV -> metadata generica -> endpoint REST -> secuencia CSV -> juez_respuesta -> juez_metricas -> reporte
```

Carpetas y archivos principales:

```text
data/agentes_agenticos.csv
adapters/agentico_rest/
adapters/agentico_rest/agent.py
adapters/agentico_rest/client.py
evaluation/juez_respuesta.py
evaluation/juez_metricas.py
reporting/report.py
```

Consideraciones:

- No usa `user_simulator`.
- No usa prompts `AR`, `I` ni `R`.
- No usa `BOT_API_KEY`, `URL_CHAT` ni `CUSTOMER_PROC_URL`.
- Usa `secuencia_mensaje` del CSV para conducir los turnos adicionales.
- El perfil recomendado es `agentico_default`, porque usa juez de respuesta mas metricas.

### 3. Ejecucion Con Nuevo Adapter IA-AGENT

Esta ejecucion no existe como adapter concreto todavia, pero el framework ya esta preparado para agregarla.

Requiere crear una carpeta nueva:

```text
adapters/mi_nuevo_agente/
```

Y registrar el adapter en:

```text
adapters/factory.py
config.py
```

Contrato minimo que debe implementar:

```python
class MiNuevoAgenteClient:
    name = "mi_nuevo_agente"

    def prepare_scenario(self, scenario_data):
        ...

    def start_chat(self, prepared):
        ...

    def send_message(self, session, message):
        ...
```

Capacidad opcional:

```python
def simulate_user(self, scenario, prepared, history):
    ...
```

Cuando se agrega esta capacidad, el runner puede continuar la conversacion con simulador. Si no se agrega, el flujo sigue siendo valido y se ejecuta con `mensaje_inicio` mas `secuencia_mensaje`.

Resumen:

```text
1. phoenix        Ejecucion real especializada para Phoenix/cobranzas.
2. agentico_rest Ejecucion real generica para agentes IA-AGENT por REST.
3. nuevo adapter Ejecucion extensible para otro agente agentico.
```

## Configuracion Comun

Todas las variables se leen desde `.env.<ambiente>`, por ejemplo `.env.desa`.

```env
APP_ENV=desa
AGENT_ADAPTER=phoenix
TIPO_AGENTE=agentico
EVAL_PROFILE=phoenix_cobranzas

CSV_PATH=.\data\casos_de_prueba_desa.csv
CSV_SEP=;
OUTPUT_DIR=.\resultados
REPORT_TITLE=Reporte de Evaluacion IA-AGENT

MAX_TURNS_SAFE=5
MAX_WORKERS=3
DEBUG_HTTP=0
```

Variables para jueces LLM:

```env
AZURE_OPENAI_ENDPOINT=https://...
AZURE_OPENAI_API_VERSION=...
AZURE_OPENAI_API_KEY=...
MODEL_NAME=...
```

No versionar archivos `.env.*`. El repo ya los ignora mediante `.gitignore`.

## Modo Phoenix

Usa este modo cuando ejecutes el agente Phoenix/cobranzas.

```env
AGENT_ADAPTER=phoenix
TIPO_AGENTE=agentico
EVAL_PROFILE=phoenix_cobranzas

CSV_PATH=.\data\casos_de_prueba_desa.csv
CSV_SEP=;

BOT_API_KEY=...
URL_CHAT=https://...
CUSTOMER_PROC_URL=https://...
```

Flujo:

```text
CSV -> Phoenix payload -> customer proc -> chat Phoenix -> user simulator -> jueces -> reporte
```

En Phoenix:

```text
adapters/phoenix/payload.py      construye customer_data.
adapters/phoenix/client.py       llama los endpoints Phoenix.
adapters/phoenix/prompts.py      contiene prompts AR/I/R.
adapters/phoenix/simulator.py    simula cliente con Azure OpenAI.
```

## Modo Agentico REST

Usa este modo cuando quieras evaluar un agente IA-AGENT distinto de Phoenix que expone un endpoint REST.

```env
AGENT_ADAPTER=agentico_rest
TIPO_AGENTE=agentico
EVAL_PROFILE=agentico_default

CSV_PATH=.\data\agentes_agenticos.csv
CSV_SEP=;

AGENTICO_REST_URL=https://tu-api/agente
AGENTICO_REST_API_KEY=opcional
AGENTICO_REST_AUTH_HEADER=X-API-key
AGENTICO_REST_PAYLOAD_MODE=default
AGENTICO_REST_RESPONSE_FIELD=respuesta
AGENTICO_REST_TIMEOUT=600
AGENTICO_REST_VERIFY_SSL=1
```

Este adapter no usa:

```text
BOT_API_KEY
URL_CHAT
CUSTOMER_PROC_URL
user_simulator
prompts AR/I/R
juez_funcionalidades
```

Si `AGENTICO_REST_PAYLOAD_MODE=default`, el framework envia:

```json
{
  "message": "mensaje del usuario",
  "session_id": "CP001",
  "id_test": "CP001",
  "history": [],
  "metadata": {}
}
```

Si tu API solo acepta el mensaje:

```env
AGENTICO_REST_PAYLOAD_MODE=message_only
```

Y se enviara:

```json
{
  "message": "mensaje del usuario"
}
```

Por defecto el adapter intenta extraer la respuesta desde campos comunes:

```text
content
answer
respuesta
response
text
message
message.content
output
result
data.content
data.answer
data.respuesta
choices.0.message.content
```

Si tu API responde en un campo especifico:

```env
AGENTICO_REST_RESPONSE_FIELD=respuesta
```

## CSV De Entrada

### CSV Phoenix

Archivo usado normalmente:

```text
data/casos_de_prueba_desa.csv
```

Incluye columnas especificas de cobranzas, por ejemplo `tipo_cliente`, `tipo_seg`, `deuda_soles`, `dni`, `cic`, `reglas_muy_importante`, etc.

### CSV Agentico Generico

Archivo disponible:

```text
data/agentes_agenticos.csv
```

Columnas minimas:

```text
id_test
caso_de_prueba
mensaje_inicio
secuencia_mensaje
ejecutar_prueba
```

Ejemplo:

```csv
id_test;caso_de_prueba;mensaje_inicio;secuencia_mensaje;ejecutar_prueba
CP001;Validar que el agente registre una promesa de pago;no puedo pagar;Deseo registrar una promesa de pago para el viernes;1
```

`secuencia_mensaje` puede contener varios mensajes separados por saltos de linea.

## Reportes

Al terminar, `main.py` genera:

```text
Rep-paralelizado-<fecha>.html
Rep-paralelizado-<fecha>.csv
```

en la carpeta configurada con:

```env
OUTPUT_DIR=.\resultados
```

## Pruebas

Ejecutar todas las pruebas:

```powershell
python -m unittest
```

Prueba de humo de prompts/evaluacion:

```powershell
python -m unittest tests.test_smoke_eval
```

Pruebas del runner y adapters:

```powershell
python -m unittest tests.test_adapter_runner
```

## Agregar Un Nuevo Adapter IA-AGENT

Para conectar otro agente:

1. Crear carpeta en `adapters/<nombre_adapter>/`.
2. Implementar una clase que cumpla `AgentClient` de `core/contracts.py`.
3. Registrar el adapter en `adapters/factory.py`.
4. Agregar el nombre en `AGENT_ADAPTERS_PERMITIDOS` dentro de `config.py`.
5. Definir las variables de entorno propias del adapter.
6. Agregar pruebas sin llamadas reales de red.

Contrato minimo:

```python
class MiAdapter:
    name = "mi_adapter"

    def prepare_scenario(self, scenario_data):
        ...

    def start_chat(self, prepared):
        ...

    def send_message(self, session, message):
        ...
```

Si el adapter necesita simular al usuario, puede implementar esta capacidad opcional:

```python
def simulate_user(self, scenario, prepared, history):
    ...
```

## Seguridad

- No subir `.env.*` al repositorio.
- No imprimir tokens o respuestas completas de servicios externos si contienen datos sensibles.
- Mantener `DEBUG_HTTP=0` por defecto.
- En produccion preferir variables de entorno del servidor o un secret manager.
- No guardar `CONFIRM_PROD` dentro de `.env.prod`; definirlo en consola por cada ejecucion productiva.

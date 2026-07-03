# framework_base_agentes

Framework base para ejecutar y evaluar agentes conversacionales que usan IA generativa o flujos agenticos. Permite leer escenarios desde CSV, ejecutar conversaciones contra un agente externo, evaluar la conversacion con jueces LLM y generar reportes HTML/CSV.

La arquitectura actual separa el nucleo del framework de las implementaciones concretas de agentes:

```text
core/                  Orquestacion generica de escenarios.
adapters/              Integraciones concretas con agentes externos.
integrations/          Clientes reutilizables, como Azure OpenAI.
evaluation/            Jueces de respuesta, funcionalidades y metricas.
reporting/             Generacion de reportes HTML y CSV.
data/                  CSV de entrada.
resultados/            Reportes generados.
```

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
|   |-- no_agentico_rest/
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
|   |-- agentes_no_agentico.csv
```

## Conceptos

### Adapter

Un adapter es la pieza que sabe hablar con un agente externo.

Adapters disponibles:

```text
phoenix             Agente Phoenix/cobranzas.
no_agentico_rest    Agente no agentico expuesto por API REST.
```

Se selecciona con:

```env
AGENT_ADAPTER=phoenix
```

Si no se define `AGENT_ADAPTER`, el framework usa `phoenix` por compatibilidad.

### Tipo de agente

`TIPO_AGENTE` define como se ejecuta la conversacion:

```text
agentico       Usa secuencia del CSV + user simulator.
hibrido        Usa secuencia del CSV + user simulator.
no_agentico    Usa solo mensaje inicial + secuencia del CSV.
```

Importante: el `user_simulator` y los prompts `AR`, `I` y `R` son exclusivos del adapter Phoenix. El adapter `no_agentico_rest` no implementa simulador.

### Perfil de evaluacion

`EVAL_PROFILE` define que jueces se ejecutan:

```text
phoenix_cobranzas     juez_funcionalidades + juez_metricas
generic_agentic       juez_respuesta + juez_metricas
no_agentico_default   juez_respuesta + juez_metricas
```

La evaluacion de metricas en `evaluation/juez_metricas.py` puede usarse con cualquier adapter.

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

## Configuracion Comun

Todas las variables se leen desde `.env.<ambiente>`, por ejemplo `.env.desa`.

Variables comunes:

```env
APP_ENV=desa
AGENT_ADAPTER=phoenix
TIPO_AGENTE=agentico
EVAL_PROFILE=phoenix_cobranzas

CSV_PATH=.\data\casos_de_prueba_desa.csv
CSV_SEP=;
OUTPUT_DIR=.\resultados
REPORT_TITLE=Reporte de Evaluacion

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

Configuracion recomendada:

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
CSV -> Phoenix payload -> customer proc -> chat Phoenix -> user simulator opcional -> jueces -> reporte
```

En Phoenix:

```text
adapters/phoenix/payload.py      construye customer_data.
adapters/phoenix/client.py       llama los endpoints Phoenix.
adapters/phoenix/prompts.py      contiene prompts AR/I/R.
adapters/phoenix/simulator.py    simula cliente con Azure OpenAI.
```

## Modo No Agentico REST

Usa este modo cuando quieras evaluar un agente no Phoenix que expone un endpoint REST.

Configuracion recomendada:

```env
AGENT_ADAPTER=no_agentico_rest
TIPO_AGENTE=no_agentico
EVAL_PROFILE=no_agentico_default

CSV_PATH=.\data\agentes_no_agentico.csv
CSV_SEP=;

NO_AGENTICO_REST_URL=https://tu-api/agente
NO_AGENTICO_REST_API_KEY=opcional
NO_AGENTICO_REST_AUTH_HEADER=X-API-key
NO_AGENTICO_REST_PAYLOAD_MODE=default
NO_AGENTICO_REST_RESPONSE_FIELD=respuesta
NO_AGENTICO_REST_TIMEOUT=600
NO_AGENTICO_REST_VERIFY_SSL=1
```

En este modo no se usan:

```text
BOT_API_KEY
URL_CHAT
CUSTOMER_PROC_URL
user_simulator
prompts AR/I/R
juez_funcionalidades
```

Si `NO_AGENTICO_REST_PAYLOAD_MODE=default`, el framework envia:

```json
{
  "message": "mensaje del usuario",
  "session_id": "CP001",
  "id_test": "CP001",
  "history": [],
  "metadata": {}
}
```

Si tu API solo acepta el mensaje, usa:

```env
NO_AGENTICO_REST_PAYLOAD_MODE=message_only
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

Si tu API responde en un campo especifico, define:

```env
NO_AGENTICO_REST_RESPONSE_FIELD=respuesta
```

## CSV De Entrada

### CSV Phoenix

Archivo usado normalmente:

```text
data/casos_de_prueba_desa.csv
```

Incluye columnas especificas de cobranzas, por ejemplo `tipo_cliente`, `tipo_seg`, `deuda_soles`, `dni`, `cic`, `reglas_muy_importante`, etc.

### CSV No Agentico

Archivo disponible:

```text
data/agentes_no_agentico.csv
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
CP001;Validar respuesta ante solicitud inicial;hola;dame mas detalle;1
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

## Agregar Un Nuevo Adapter

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

Si el adapter necesita simular usuario para modo `agentico` o `hibrido`, puede implementar la capacidad opcional:

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

# framework_base_agentes

Version 1.0.0 de la base de framework para evaluacion de agentes conversacionales. Permite ejecutar escenarios definidos en CSV, evaluar funcionalidades y metricas, y generar reportes en HTML y CSV.
## Archivos

```text
main.py           Punto de entrada: lee CSV, ejecuta escenarios y genera reporte.
config.py         Variables de entorno, rutas, endpoints y workers.
requirements.txt  Dependencias del proyecto.

core/             Logica principal del flujo.
integrations/     Llamadas externas: Azure OpenAI, Phoenix Agent y customer proc.
evaluation/       Orquestador y jueces de funcionalidades, metricas y respuesta.
reporting/        Generacion del HTML y CSV final.
data/             Archivos de entrada o ejemplos de CSV.
reportes/         Salidas generadas por ambiente.
```

## Estructura

```text
framework_base_agentes/
|-- main.py
|-- config.py
|-- requirements.txt
|-- README.md
|-- .env.desa
|-- .env.certi
|-- .env.prod
|
|-- core/
|   |-- runner.py
|   |-- simulator.py
|   |-- prompts.py
|   |-- utils.py
|
|-- integrations/
|   |-- clients.py
|
|-- evaluation/
|   |-- juez.py
|   |-- juez_metricas.py
|   |-- juez_funcionalidades.py
|   |-- juez_respuesta.py
|
|-- reporting/
|   |-- report.py
|
|-- data/
|   |-- README.md
|
|-- resultados/
```

La raiz conserva solo el arranque, configuracion y metadatos del proyecto. La logica se agrupa por finalidad para evitar una estructura grande antes de necesitarla.

## Ejecucion

```powershell
pip install -r requirements.txt
python main.py
```

Prueba de humo (sin llamadas externas) para validar que los prompts de evaluacion se construyen correctamente:

```powershell
python -m unittest tests.test_smoke_eval
```

Si no defines `APP_ENV`, se usa `desa` automaticamente y se carga `.env.desa`.

```powershell
$env:APP_ENV="certi"
python main.py
```

Para `prod` se requiere una confirmacion adicional en la consola:

```powershell
$env:APP_ENV="prod"
$env:CONFIRM_PROD="1"
python main.py
```

## Ambientes

El proyecto soporta tres ambientes:

```text
desa
certi
prod
```

Cada ambiente carga su propio archivo `.env.<ambiente>`:

```text
.env.desa     valores reales de DESA, no se versiona
.env.certi    valores reales de CERTI, no se versiona
.env.prod     valores reales de PROD, no se versiona
```

`APP_ENV` es opcional. Si no se define, `config.py` usa `desa`; si se define, carga el archivo `.env.<ambiente>` correspondiente y valida que existan todas las variables requeridas antes de ejecutar pruebas.

## Tipo de agente

El tipo de evaluacion se controla desde el archivo `.env.<ambiente>`:

```env
TIPO_AGENTE=agentico
```

Valores permitidos:

```text
agentico
hibrido
no_agentico
```

Flujo de conversacion por tipo:

```text
agentico      usa secuencia de CSV + user simulator
hibrido       usa secuencia de CSV + user simulator
no_agentico   usa solo secuencia de CSV (sin user simulator)
```

Pipeline de evaluacion (configurable) con `EVAL_PROFILE`:

```text
phoenix_cobranzas   juez de funcionalidades + metricas
generic_agentic     juez de respuesta + metricas
no_agentico_default juez de respuesta + metricas
```

Por defecto:

```text
TIPO_AGENTE=no_agentico    -> EVAL_PROFILE=no_agentico_default
TIPO_AGENTE=agentico/hibrido -> EVAL_PROFILE=phoenix_cobranzas
```

### Matriz de combinaciones posibles

| TIPO_AGENTE | EVAL_PROFILE | Permitido | Recomendado | Resultado esperado |
|---|---|---|---|---|
| `agentico` | `phoenix_cobranzas` | Si | Si | Flujo agentico + juez funcionalidades + metricas |
| `agentico` | `generic_agentic` | Si | Si (agente no Phoenix) | Flujo agentico + juez respuesta + metricas |
| `agentico` | `no_agentico_default` | Si | No | Flujo agentico + juez respuesta + metricas |
| `hibrido` | `phoenix_cobranzas` | Si | Si | Flujo hibrido + juez funcionalidades + metricas |
| `hibrido` | `generic_agentic` | Si | Si (agente no Phoenix) | Flujo hibrido + juez respuesta + metricas |
| `hibrido` | `no_agentico_default` | Si | No | Flujo hibrido + juez respuesta + metricas |
| `no_agentico` | `phoenix_cobranzas` | Si | No | Flujo no_agentico + juez funcionalidades + metricas |
| `no_agentico` | `generic_agentic` | Si | Si | Flujo no_agentico + juez respuesta + metricas |
| `no_agentico` | `no_agentico_default` | Si | Si | Flujo no_agentico + juez respuesta + metricas |

Ejemplos recomendados de `.env`:

```env
# 1) Phoenix cobranzas (agentico)
TIPO_AGENTE=agentico
EVAL_PROFILE=phoenix_cobranzas

# 2) Phoenix cobranzas (hibrido)
TIPO_AGENTE=hibrido
EVAL_PROFILE=phoenix_cobranzas

# 3) No agentico estandar
TIPO_AGENTE=no_agentico
EVAL_PROFILE=no_agentico_default

# 4) Agente no Phoenix (agentico/hibrido/no_agentico)
TIPO_AGENTE=agentico
EVAL_PROFILE=generic_agentic
```

Para el perfil `phoenix_cobranzas`, el orquestador de evaluacion ejecuta:

```text
evaluation/juez_funcionalidades.py
evaluation/juez_metricas.py
```

Para los perfiles `generic_agentic` y `no_agentico_default`, ejecuta:

```text
evaluation/juez_respuesta.py
evaluation/juez_metricas.py
```

`evaluation/juez.py` queda como orquestador y mantiene los imports usados por `runner.py` y `reporting/report.py`.

## Variables de entorno

Todas las variables de configuracion deben venir del archivo `.env.<ambiente>`:

```text
AZURE_OPENAI_API_KEY
AZURE_OPENAI_ENDPOINT
AZURE_OPENAI_API_VERSION
MODEL_NAME
BOT_API_KEY
URL_CHAT
CUSTOMER_PROC_URL
CSV_PATH
CSV_SEP
OUTPUT_DIR
REPORT_TITLE (opcional)
MAX_TURNS_SAFE
MAX_WORKERS
DEBUG_HTTP
TIPO_AGENTE
EVAL_PROFILE
```

`REPORT_TITLE` es opcional y permite personalizar el titulo visible del reporte HTML y de la pestana del navegador.

Recomendacion por ambiente:

```text
.env.desa   OUTPUT_DIR=.\reportes\desa
.env.certi  OUTPUT_DIR=.\reportes\certi
.env.prod   OUTPUT_DIR=.\reportes\prod
```

No guardar `CONFIRM_PROD` dentro de `.env.prod`. Debe definirse en la consola para cada ejecucion productiva, asi se evita correr contra `prod` por accidente.

## Nota de migracion

Esta version conserva la logica principal del `user_final.py`, pero organizada en archivos simples. La recomendacion es validar primero con pocos escenarios en `desa`, luego repetir en `certi` y usar `prod` solo con confirmacion explicita.

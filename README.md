# framework_base_agentes

Version simple y plana de `user_final.py`, separada por responsabilidad sin crear una estructura grande.

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
|-- reportes/
```

La raiz conserva solo el arranque, configuracion y metadatos del proyecto. La logica se agrupa por finalidad para evitar una estructura grande antes de necesitarla.

## Ejecucion

```powershell
pip install -r requirements.txt
python main.py
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
no_agentico
```

Para un agente `agentico`, el orquestador ejecuta:

```text
evaluation/juez_funcionalidades.py
evaluation/juez_metricas.py
```

Para un agente `no_agentico`, el orquestador ejecuta:

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
MAX_TURNS_SAFE
MAX_WORKERS
DEBUG_HTTP
TIPO_AGENTE
```

Recomendacion por ambiente:

```text
.env.desa   OUTPUT_DIR=.\reportes\desa
.env.certi  OUTPUT_DIR=.\reportes\certi
.env.prod   OUTPUT_DIR=.\reportes\prod
```

No guardar `CONFIRM_PROD` dentro de `.env.prod`. Debe definirse en la consola para cada ejecucion productiva, asi se evita correr contra `prod` por accidente.

## Nota de migracion

Esta version conserva la logica principal del `user_final.py`, pero organizada en archivos simples. La recomendacion es validar primero con pocos escenarios en `desa`, luego repetir en `certi` y usar `prod` solo con confirmacion explicita.

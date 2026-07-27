# configuracion

## Proposito

Esta carpeta contiene la lectura y validacion de variables de entorno.

El framework usa estas variables para saber:

- que agente evaluar;
- como conectarse al agente;
- como conectarse al modelo juez;
- donde guardar el reporte;
- limites de tiempo y longitud de texto.

## Archivos

### `variables.py`

Define la clase `Settings`.

Responsabilidades:

- leer variables desde el entorno;
- validar URLs;
- proteger secretos con `SecretStr`;
- validar el endpoint de Foundry;
- normalizar configuracion de Dify;
- limitar valores como timeout y longitud maxima.

Variables principales:

- `AGENT_PROVIDER`;
- `AGENT_BASE_URL`;
- `AGENT_ENDPOINT`;
- `AGENT_API_KEY`;
- `DIFY_BASE_URL`;
- `DIFY_API_KEY`;
- `FOUNDRY_ENDPOINT`;
- `FOUNDRY_API_KEY`;
- `FOUNDRY_MODEL`;
- `REPORT_DIRECTORY`.

### `__init__.py`

Exporta `Settings` y `get_settings` para que otros modulos puedan leer configuracion sin conocer el archivo interno.

## Flujo

```text
.env.desa
  |
  v
evaluador/configuracion/variables.py
  |
  v
evaluador/ejecucion.py
```

## Cuando modificar esta carpeta

Modifica esta carpeta cuando agregues una nueva variable de entorno o un nuevo adaptador que necesite configuracion propia.


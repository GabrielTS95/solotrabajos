# datos

## Proposito

Esta carpeta contiene la lectura del dataset de evaluacion.

Su trabajo es convertir el CSV en objetos `TestCase` que el resto del framework pueda usar.

## Archivos

### `leer_casos.py`

Lee y valida `datasets/test_cases.csv`.

Hace lo siguiente:

1. Verifica que el archivo exista.
2. Lee el CSV con encabezados.
3. Normaliza nombres de columnas.
4. Permite algunos alias de columnas, como `pregunta` para `query`.
5. Convierte listas y numeros cuando corresponde.
6. Valida cada fila usando el modelo `TestCase`.
7. Rechaza IDs duplicados.

### `__init__.py`

Exporta `load_test_cases` y `DatasetError`.

## Campos basicos esperados

```csv
id,category,query,expected_behavior
```

## Flujo

```text
datasets/test_cases.csv
  |
  v
evaluador/datos/leer_casos.py
  |
  v
evaluador/evaluacion/modelos.py
```

## Cuando modificar esta carpeta

Modifica esta carpeta si cambias el formato del dataset o agregas nuevos campos al CSV.


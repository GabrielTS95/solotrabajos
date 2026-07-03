#Importa datetime para capturar hora inicio/fin y medir duración
from datetime import datetime
#Importa pandas (alias pd) para leer y manipular el CSV
import pandas as pd

#Trae variables de configuración ya validadas desde config.py
from config import APP_ENV, CSV_PATH, CSV_SEP, ENV_FILE, OUTPUT_DIR
# APP_ENV   => Ambiente activo
# CSV_PATH  => Ruta del CSV
# CSV_SEP   => Separador del CSV
# ENV_FILE  => Archivo .env cargado
# OUTPUT_DIR=> Carpeta de salida de reportes

#Importa la función que corre los escenarios (en paralelo)
from core.runner import ejecutar_escenarios_en_paralelo

#Importa utilitario para formatear duración en formato legible (h:m:s)
from core.utils import format_td_hms
#Importa función que construye y guarda el reporte final
from reporting.report import generar_reporte


#Define función auxiliar para cargar y filtrar escenarios del CSV
def cargar_escenarios():
    #Empieza la lectuta del CSV hacia un DataFrame df_users
    df_users = pd.read_csv(
        #Usa ruta del archivo definida por entorno(.env)
        CSV_PATH,
        #Usa separador configurado (;,,,,etc.)
        sep=CSV_SEP,
        #Lee el archivo en codificación UTF-8
        encoding="utf-8",
        #Fuerza engine de parseo Python en lugar del engine C de pandas.
        engine="python",
        #Configura manejo de comillas en el CSV (1 corresponde a csv.QUOTE_ALL).
        quoting=1,
    )
    #Filtra solo filas con ejecutar_prueba == 1 (casos habilitados) y retorna una copia.
    return df_users[df_users["ejecutar_prueba"] == 1].copy()


#Define la función principal de ejecución del programa.
def main():
    #Muestra en consala que ambientes esta corriendo y que .env se cargo.
    print(f"Ambiente activo: {APP_ENV} ({ENV_FILE.name})")

    #Carga escenarios desde CSV ya filtrados para ejecución.
    df_users_ejecutar = cargar_escenarios()

    #Captura timestamp de inicio global del proceso.
    global_start = datetime.now()
    rows, total_exec_time = ejecutar_escenarios_en_paralelo(df_users_ejecutar)
    global_end = datetime.now()
    wall_exec_time = global_end - global_start

    #Inicia llamada para generar reporte de salida.
    generar_reporte(
        rows=rows,
        total_exec_time=total_exec_time,
        wall_exec_time=wall_exec_time,
        output_dir=OUTPUT_DIR,
    )

    print("Tiempo escenarios:", format_td_hms(total_exec_time))
    print("Tiempo total:", format_td_hms(wall_exec_time))


if __name__ == "__main__":
    #Ejecuta la función principal.
    main()

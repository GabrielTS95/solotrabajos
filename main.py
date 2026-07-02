from datetime import datetime

import pandas as pd

from config import APP_ENV, CSV_PATH, CSV_SEP, ENV_FILE, OUTPUT_DIR
from core.runner import ejecutar_escenarios_en_paralelo
from core.utils import format_td_hms
from reporting.report import generar_reporte


def cargar_escenarios():
    df_users = pd.read_csv(
        CSV_PATH,
        sep=CSV_SEP,
        encoding="utf-8",
        engine="python",
        quoting=1,
    )
    return df_users[df_users["ejecutar_prueba"] == 1].copy()


def main():
    print(f"Ambiente activo: {APP_ENV} ({ENV_FILE.name})")

    df_users_ejecutar = cargar_escenarios()

    global_start = datetime.now()
    rows, total_exec_time = ejecutar_escenarios_en_paralelo(df_users_ejecutar)
    global_end = datetime.now()
    wall_exec_time = global_end - global_start

    generar_reporte(
        rows=rows,
        total_exec_time=total_exec_time,
        wall_exec_time=wall_exec_time,
        output_dir=OUTPUT_DIR,
    )

    print("Tiempo escenarios:", format_td_hms(total_exec_time))
    print("Tiempo total:", format_td_hms(wall_exec_time))


if __name__ == "__main__":
    main()

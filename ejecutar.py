from dotenv import load_dotenv

from evaluador.ejecucion import main


if __name__ == "__main__":
    load_dotenv(".env.desa")
    raise SystemExit(main())

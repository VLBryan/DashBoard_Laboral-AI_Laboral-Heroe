# config.py
import os
from dotenv import load_dotenv

load_dotenv()

try:
    import config_private
    DB_NAME = config_private.DB_NAME
    MONGO_URI = config_private.MONGO_URI
    CACHE_DIR = config_private.CACHE_DIR
except ImportError:
    # fallback si no existe el archivo (ej. en despliegue público)
    DB_NAME = os.getenv("LABORAL_DB", "nombre_de_tu_db")
    MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
    CACHE_DIR = os.getenv("CACHE_DIR", "./cache")

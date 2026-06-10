# scripts/run_etl.py
"""Ejecuta el ETL (Mongo -> df_master / df_user_skills) y refresca el cache Parquet.

Uso:
    python scripts/run_etl.py
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from config import DB_NAME, MONGO_URI, CACHE_DIR
from src.data_loader import build_all

if __name__ == "__main__":
    build_all(DB_NAME, MONGO_URI, cache_dir=CACHE_DIR)
    print(f"Cache actualizado en {CACHE_DIR}")

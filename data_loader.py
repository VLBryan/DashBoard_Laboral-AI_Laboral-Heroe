# data_loader.py
import os
from typing import List, Dict, Optional
import pandas as pd
from pymongo import MongoClient
from datetime import datetime
import json

# -------------------------
# Configuración / Conexión
# -------------------------
def get_mongo_client(uri: Optional[str] = None) -> MongoClient:
    uri = uri or os.getenv("MONGO_URI", "mongodb://localhost:27017")
    return MongoClient(uri)

def get_collection_df(client: MongoClient, db_name: str, coll_name: str) -> pd.DataFrame:
    db = client[db_name]
    cursor = db[coll_name].find()
    df = pd.DataFrame(list(cursor))
    return df

# -------------------------
# Normalizaciones comunes
# -------------------------
def ensure_datetime(df: pd.DataFrame, cols: List[str]) -> pd.DataFrame:
    for c in cols:
        if c in df.columns:
            df[c] = pd.to_datetime(df[c], errors='coerce')
    return df

def normalize_location(df: pd.DataFrame, location_col: str = "location") -> pd.DataFrame:
    # Intenta extraer país/provincia/ciudad si location es string "Country / Region / City"
    if location_col in df.columns:
        def split_loc(x):
            if pd.isna(x): return {"country": None, "region": None, "city": None}
            if isinstance(x, dict):
                return {
                    "country": x.get("country") or x.get("pais") or None,
                    "region": x.get("region") or x.get("state") or None,
                    "city": x.get("city") or x.get("ciudad") or None
                }
            s = str(x)
            parts = [p.strip() for p in s.split("/") if p.strip()]
            return {
                "country": parts[0] if len(parts) > 0 else None,
                "region": parts[1] if len(parts) > 1 else None,
                "city": parts[2] if len(parts) > 2 else None
            }
        locs = df[location_col].apply(split_loc).apply(pd.Series)
        df = pd.concat([df, locs], axis=1)
    return df

def explode_list_field(df: pd.DataFrame, id_col: str, list_col: str, new_col_name: str = "item"):
    # Si list_col contiene listas o strings JSON, normaliza y explota
    if list_col not in df.columns:
        return pd.DataFrame(columns=[id_col, new_col_name])
    def to_list(x):
        if pd.isna(x): return []
        if isinstance(x, list): return x
        try:
            parsed = json.loads(x)
            if isinstance(parsed, list): return parsed
        except Exception:
            pass
        # fallback: comma separated
        return [s.strip() for s in str(x).split(",") if s.strip()]
    s = df[[id_col, list_col]].copy()
    s[list_col] = s[list_col].apply(to_list)
    s = s.explode(list_col).rename(columns={list_col: new_col_name})
    s = s.dropna(subset=[new_col_name])
    return s[[id_col, new_col_name]]

# -------------------------
# Cargas y joins principales
# -------------------------
def load_collections(client: MongoClient, db_name: str, collections: List[str]) -> Dict[str, pd.DataFrame]:
    out = {}
    for c in collections:
        try:
            out[c] = get_collection_df(client, db_name, c)
        except Exception as e:
            print(f"Warning: no se pudo cargar {c}: {e}")
            out[c] = pd.DataFrame()
    return out

def build_df_master(dfs: Dict[str, pd.DataFrame]) -> pd.DataFrame:
    users = dfs.get("users", pd.DataFrame()).copy()
    cvs = dfs.get("cvs", pd.DataFrame()).copy()
    emp = dfs.get("employabilities", pd.DataFrame()).copy()
    apps = dfs.get("applications", pd.DataFrame()).copy()  # si existe

    # Normalizaciones básicas
    users = ensure_datetime(users, ["createdAt", "updatedAt", "deletedAt"])
    cvs = ensure_datetime(cvs, ["createdAt", "updatedAt"])
    emp = ensure_datetime(emp, ["createdAt", "updatedAt"])
    apps = ensure_datetime(apps, ["createdAt", "updatedAt"])

    # Normalizar ubicaciones
    users = normalize_location(users, "location")
    cvs = normalize_location(cvs, "location")

    # Merge users <- cvs (traer profession y cv_id)
    if not cvs.empty:
        cvs_small = cvs.rename(columns={"_id": "cv_id", "user": "user_id"})
        cvs_small = cvs_small[["cv_id", "user_id", "profession", "location", "createdAt"]].drop_duplicates(subset=["user_id"], keep="first")
        df = users.merge(cvs_small, left_on="_id", right_on="user_id", how="left", suffixes=("","_cv"))
    else:
        df = users.copy()
        df["cv_id"] = None
        df["profession"] = None

    # Merge employabilities
    if not emp.empty:
        emp_small = emp.rename(columns={"user": "user_id"})[["user_id", "score", "level", "suggested_role"]]
        df = df.merge(emp_small, left_on="_id", right_on="user_id", how="left")
    else:
        df["score"] = None
        df["level"] = None
        df["suggested_role"] = None

    # Count aplicaciones por usuario
    if not apps.empty:
        apps_count = apps.groupby("user").size().rename("n_applications").reset_index()
        df = df.merge(apps_count, left_on="_id", right_on="user", how="left")
        df["n_applications"] = df["n_applications"].fillna(0).astype(int)
    else:
        df["n_applications"] = 0

    # Flag Laboral Hero
    df["is_laboral_hero"] = df["invitationCode"].notna() & (df["invitationCode"].astype(str).str.strip() != "")

    # Top skills placeholder (llenar con función aparte)
    df["top_skills"] = None

    # Limpieza final
    df = df.rename(columns={"_id": "user_id"})
    return df



# -------------------------
# Skills por usuario
# -------------------------
def build_df_user_skills(dfs: Dict[str, pd.DataFrame]) -> pd.DataFrame:
    cvs_sk = dfs.get("cvs_skills", pd.DataFrame()).copy()
    skills = dfs.get("skills", pd.DataFrame()).copy()
    cvs = dfs.get("cvs", pd.DataFrame()).copy()

    if cvs_sk.empty:
        return pd.DataFrame(columns=["user_id", "skill_id", "skill_name", "order"])

    # cvs_sk expected: id_cvs, id_skills, order
    cvs_map = cvs[["_id", "user"]].rename(columns={"_id": "cv_id", "user": "user_id"})
    cvs_sk = cvs_sk.rename(columns={"id_cvs": "cv_id", "id_skills": "skill_id"})
    merged = cvs_sk.merge(cvs_map, on="cv_id", how="left")
    if not skills.empty:
        skills_small = skills.rename(columns={"_id": "skill_id", "name": "skill_name"})[["skill_id", "skill_name"]]
        merged = merged.merge(skills_small, on="skill_id", how="left")
    else:
        merged["skill_name"] = merged["skill_id"]

    merged = merged[["user_id", "skill_id", "skill_name", "order"]]
    merged["skill_name"] = merged["skill_name"].astype(str)
    # contar ocurrencias por usuario-skill
    agg = merged.groupby(["user_id", "skill_name"]).size().rename("count").reset_index()
    agg = agg.sort_values(["user_id", "count"], ascending=[True, False])
    return agg

# -------------------------
# Enriquecer df_master con top skills
# -------------------------
def enrich_master_with_skills(df_master: pd.DataFrame, df_user_skills: pd.DataFrame, top_n: int = 5) -> pd.DataFrame:
    if df_user_skills.empty:
        df_master["top_skills"] = df_master["top_skills"].fillna("").astype(str)
        return df_master
    top = df_user_skills.groupby("user_id").apply(lambda g: ", ".join(g.sort_values("count", ascending=False)["skill_name"].head(top_n))).rename("top_skills").reset_index()
    df_master = df_master.merge(top, left_on="user_id", right_on="user_id", how="left")
    df_master["top_skills"] = df_master["top_skills"].fillna("")
    return df_master

# -------------------------
# Cache / persistencia simple
# -------------------------
def save_df_cache(df: pd.DataFrame, path: str):
    df.to_parquet(path, index=False)

def load_df_cache(path: str) -> pd.DataFrame:
    return pd.read_parquet(path)

# -------------------------
# Función principal de orquestación
# -------------------------
def build_all(db_name: str, mongo_uri: Optional[str] = None, cache_dir: str = "./cache") -> Dict[str, pd.DataFrame]:
    client = get_mongo_client(mongo_uri)
    collections = ["users","cvs","employabilities","cvs_skills","skills","applications","courseenrollments","quizresults","userquizdatas","payments","notifications","educations","companies"]
    dfs = load_collections(client, db_name, collections)

    df_master = build_df_master(dfs)
    df_user_skills = build_df_user_skills(dfs)
    df_master = enrich_master_with_skills(df_master, df_user_skills, top_n=5)

    os.makedirs(cache_dir, exist_ok=True)
    save_df_cache(df_master, os.path.join(cache_dir, "df_master.parquet"))
    save_df_cache(df_user_skills, os.path.join(cache_dir, "df_user_skills.parquet"))

    return {"df_master": df_master, "df_user_skills": df_user_skills, **dfs}

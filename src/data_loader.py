# data_loader.py
import os
from typing import List, Dict, Optional
import pandas as pd
from pymongo import MongoClient
from datetime import datetime
import json

# Intentamos importar ObjectId para detectar y convertirlo
try:
    from bson import ObjectId
except Exception:
    ObjectId = None

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
# Utilidades de limpieza
# -------------------------
def _convert_value_for_parquet(x):
    """
    Convierte valores no serializables por pyarrow a tipos compatibles:
    - ObjectId -> str
    - dict/list -> json string
    - bytes -> decoded string
    """
    if x is None:
        return None
    if ObjectId is not None and isinstance(x, ObjectId):
        return str(x)
    if isinstance(x, (dict, list)):
        try:
            return json.dumps(x, ensure_ascii=False)
        except Exception:
            return str(x)
    if isinstance(x, (bytes, bytearray)):
        try:
            return x.decode("utf-8", errors="ignore")
        except Exception:
            return str(x)
    return x

def sanitize_dataframe_for_parquet(df: pd.DataFrame) -> pd.DataFrame:
    """
    Recorre columnas object y aplica conversiones puntuales para evitar errores
    al exportar con pyarrow (ObjectId, dicts, lists, bytes).
    """
    if df is None or df.empty:
        return df
    df = df.copy()
    for col in df.columns:
        if df[col].dtype == "object":
            df[col] = df[col].apply(_convert_value_for_parquet)
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
    if location_col in df.columns:
        def split_loc(x):
            if pd.isna(x):
                return {"country": None, "region": None, "city": None}
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
    if list_col not in df.columns:
        return pd.DataFrame(columns=[id_col, new_col_name])
    def to_list(x):
        if isinstance(x, list): return x
        if pd.isna(x): return []
        try:
            parsed = json.loads(x)
            if isinstance(parsed, list): return parsed
        except Exception:
            pass
        return [s.strip() for s in str(x).split(",") if s.strip()]
    s = df[[id_col, list_col]].copy()
    s[list_col] = s[list_col].apply(to_list)
    s = s.explode(list_col).rename(columns={list_col: new_col_name})
    s = s.dropna(subset=[new_col_name])
    return s[[id_col, new_col_name]]


import re
def normalize_colnames(df):
    df = df.copy()
    def norm(c):
        c = str(c).strip()
        c = re.sub(r"\s+", "_", c)
        c = re.sub(r"[^\w_]", "", c)
        return c.lower()
    df.columns = [norm(c) for c in df.columns]
    return df

def get_series(df: pd.DataFrame, col: str, default: str = "") -> pd.Series:
    """
    Devuelve una pd.Series garantizada: si la columna existe la devuelve,
    si no, crea una Series con el valor default y el mismo índice de df.
    """
    if col in df.columns:
        return df[col]
    return pd.Series([default] * len(df), index=df.index)


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
    """
    Construye df_master a partir de las colecciones cargadas.
    Convierte ObjectId y campos anidados a formatos compatibles antes de guardar.
    """
    users = dfs.get("users", pd.DataFrame()).copy()
    cvs = dfs.get("cvs", pd.DataFrame()).copy()
    emp = dfs.get("employabilities", pd.DataFrame()).copy()
    apps = dfs.get("applications", pd.DataFrame()).copy()

    # Sanitizar fuentes
    users = sanitize_dataframe_for_parquet(users)
    cvs = sanitize_dataframe_for_parquet(cvs)
    emp = sanitize_dataframe_for_parquet(emp)
    apps = sanitize_dataframe_for_parquet(apps)

    # Normalizaciones
    users = ensure_datetime(users, ["createdAt", "updatedAt", "deletedAt"])
    cvs = ensure_datetime(cvs, ["createdAt", "updatedAt"])
    emp = ensure_datetime(emp, ["createdAt", "updatedAt"])
    apps = ensure_datetime(apps, ["createdAt", "updatedAt"])

    # Ubicaciones
    users = normalize_location(users, "location")
    cvs = normalize_location(cvs, "location")

    # Merge users <- cvs
    if not cvs.empty:
        cvs_small = cvs.rename(columns={"_id": "cv_id", "user": "user_id"})
        cols_needed = [c for c in ["cv_id", "user_id", "profession", "location", "createdAt"] if c in cvs_small.columns]
        cvs_small = cvs_small[cols_needed].drop_duplicates(subset=["user_id"], keep="first")
        left_on = "_id" if "_id" in users.columns else ("user_id" if "user_id" in users.columns else None)
        if left_on:
            df = users.merge(cvs_small, left_on=left_on, right_on="user_id", how="left", suffixes=("","_cv"))
        else:
            df = users.copy()
            df["cv_id"] = None
            df["profession"] = None
    else:
        df = users.copy()
        df["cv_id"] = None
        df["profession"] = None

    # Merge employabilities
    if not emp.empty:
        emp_small = emp.rename(columns={"user": "user_id"})
        cols_emp = [c for c in ["user_id", "score", "level", "suggested_role"] if c in emp_small.columns]
        emp_small = emp_small[cols_emp]
        if "_id" in df.columns:
            df = df.merge(emp_small, left_on="_id", right_on="user_id", how="left")
        elif "user_id" in df.columns:
            df = df.merge(emp_small, left_on="user_id", right_on="user_id", how="left")
        else:
            if "email" in df.columns and "email" in emp_small.columns:
                df = df.merge(emp_small, left_on="email", right_on="email", how="left")
            else:
                df["score"] = None
                df["level"] = None
                df["suggested_role"] = None
    else:
        df["score"] = None
        df["level"] = None
        df["suggested_role"] = None

    # --- después de haber hecho merges y antes de return df ---
    # Asegurar columnas de fecha
    if "createdAt" not in df.columns and "createdat" in df.columns:
        df["createdAt"] = pd.to_datetime(df["createdat"], errors="coerce")
    else:
        df["createdAt"] = pd.to_datetime(df.get("createdAt"), errors="coerce")

    # Normalizar user_id: elegir la columna correcta si existe duplicada
    for cand in ["user_id", "user_id_x", "user_id_y", "user", "_id"]:
        if cand in df.columns:
            df["user_id"] = df[cand].astype(str)
            break

    # Eliminar columnas auxiliares que puedan confundir
    for c in ["user_id_x", "user_id_y", "user", "_id"]:
        if c in df.columns and c != "user_id":
            df = df.drop(columns=[c])

    # Dedupe por user_id: mantener la fila más reciente según createdAt
    if "createdAt" in df.columns:
        df = df.sort_values("createdAt", ascending=False).drop_duplicates(subset=["user_id"], keep="first").reset_index(drop=True)
    else:
        df = df.drop_duplicates(subset=["user_id"], keep="first").reset_index(drop=True)

    # Recalcular n_applications desde la colección original (apps sanitizada)
    apps = dfs.get("applications", pd.DataFrame()).copy()
    if not apps.empty:
        apps = sanitize_dataframe_for_parquet(apps)
        apps = normalize_colnames(apps) if 'normalize_colnames' in globals() else apps
        # buscar columna user en apps
        user_col = "user" if "user" in apps.columns else ("user_id" if "user_id" in apps.columns else None)
        if user_col:
            apps[user_col] = apps[user_col].astype(str)
            apps_count = apps.groupby(user_col).size().rename("n_applications").reset_index()
            apps_count = apps_count.rename(columns={user_col: "user_id"})
            df = df.merge(apps_count, on="user_id", how="left")
            df["n_applications"] = get_series(df, "n_applications", default="").fillna(0).astype(int)
        else:
            df["n_applications"] = get_series(df, "n_applications", default="").fillna(0).astype(int)
    else:
        df["n_applications"] = get_series(df, "n_applications", default="").fillna(0).astype(int)

    # Recalcular top_skills desde cvs_skills + skills + cvs
    skills_df = None
    try:
        cvs_sk = dfs.get("cvs_skills", pd.DataFrame()).copy()
        skills = dfs.get("skills", pd.DataFrame()).copy()
        cvs = dfs.get("cvs", pd.DataFrame()).copy()
        # normalizar nombres si es necesario
        if not cvs_sk.empty and not cvs.empty:
            cvs_map = cvs.rename(columns={"_id":"cv_id","user":"user_id"})[["cv_id","user_id"]]
            cvs_sk = cvs_sk.rename(columns={"id_cvs":"cv_id","id_skills":"skill_id"})
            merged = cvs_sk.merge(cvs_map, on="cv_id", how="left")
            if not skills.empty:
                skills_small = skills.rename(columns={"_id":"skill_id","name":"skill_name"})[["skill_id","skill_name"]]
                merged = merged.merge(skills_small, on="skill_id", how="left")
            merged["user_id"] = merged["user_id"].astype(str)
            skills_df = merged.groupby(["user_id","skill_name"]).size().rename("count").reset_index()
    except Exception:
        skills_df = pd.DataFrame()

    if skills_df is not None and not skills_df.empty:
        top = skills_df.groupby("user_id").apply(
            lambda g: ", ".join(g.sort_values("count", ascending=False)["skill_name"].head(5))
        ).rename("top_skills").reset_index()
        df = df.merge(top, on="user_id", how="left")
        # si existía columna previa, preferir la nueva
        if "top_skills_x" in df.columns and "top_skills_y" in df.columns:
            df["top_skills"] = df["top_skills_y"].fillna(df["top_skills_x"])
            df = df.drop(columns=["top_skills_x","top_skills_y"])
        df["top_skills"] = get_series(df, "top_skills", default="").fillna("").astype(str)
    else:
        df["top_skills"] = get_series(df, "top_skills", default="").fillna("").astype(str)

    # Recalcular is_laboral_hero desde invitationCode
    if "invitationCode" in df.columns:
        df["invitationCode"] = df["invitationCode"].replace({"None": None, "": None})
        df["is_laboral_hero"] = df["invitationCode"].notna() & (df["invitationCode"].astype(str).str.strip() != "")
    else:
        df["is_laboral_hero"] = df.get("is_laboral_hero", False).astype(bool)

    # Forzar tipos finales útiles
    df["user_id"] = get_series(df, "user_id", default="").astype(str)
    if "score" in df.columns:
        df["score"] = pd.to_numeric(df["score"], errors="coerce")

    # fin: devolver df


    return df

# -------------------------
# Skills por usuario
# -------------------------
def build_df_user_skills(dfs: Dict[str, pd.DataFrame]) -> pd.DataFrame:
    cvs_sk = dfs.get("cvs_skills", pd.DataFrame()).copy()
    skills = dfs.get("skills", pd.DataFrame()).copy()
    cvs = dfs.get("cvs", pd.DataFrame()).copy()

    cvs_sk = sanitize_dataframe_for_parquet(cvs_sk)
    skills = sanitize_dataframe_for_parquet(skills)
    cvs = sanitize_dataframe_for_parquet(cvs)

    if cvs_sk.empty:
        return pd.DataFrame(columns=["user_id", "skill_id", "skill_name", "order"])

    cvs_map = cvs[["_id", "user"]].rename(columns={"_id": "cv_id", "user": "user_id"}) if "_id" in cvs.columns and "user" in cvs.columns else pd.DataFrame(columns=["cv_id","user_id"])
    cvs_sk = cvs_sk.rename(columns={"id_cvs": "cv_id", "id_skills": "skill_id"})
    merged = cvs_sk.merge(cvs_map, on="cv_id", how="left")
    if not skills.empty and "_id" in skills.columns:
        skills_small = skills.rename(columns={"_id": "skill_id", "name": "skill_name"})[["skill_id", "skill_name"]]
        merged = merged.merge(skills_small, on="skill_id", how="left")
    else:
        merged["skill_name"] = merged["skill_id"]

    if "user" in merged.columns and "user_id" not in merged.columns:
        merged = merged.rename(columns={"user": "user_id"})
    if "user_id" not in merged.columns:
        merged["user_id"] = None

    merged = merged[["user_id", "skill_id", "skill_name", "order"]]
    merged["skill_name"] = merged["skill_name"].astype(str)
    agg = merged.groupby(["user_id", "skill_name"]).size().rename("count").reset_index()
    agg = agg.sort_values(["user_id", "count"], ascending=[True, False])
    agg["user_id"] = agg["user_id"].astype(str)
    return agg

# -------------------------
# Enriquecer df_master con top skills
# -------------------------
def enrich_master_with_skills(df_master: pd.DataFrame, df_user_skills: pd.DataFrame, top_n: int = 5) -> pd.DataFrame:
    df_master = df_master.copy()
    # Asegurar columna top_skills existe
    if "top_skills" not in df_master.columns:
        df_master["top_skills"] = None

    if df_user_skills is None or df_user_skills.empty:
        df_master["top_skills"] = df_master["top_skills"].fillna("").astype(str)
        return df_master

    # Forzar user_id string en df_user_skills
    if "user_id" in df_user_skills.columns:
        df_user_skills["user_id"] = df_user_skills["user_id"].astype(str)

    top = df_user_skills.groupby("user_id").apply(
        lambda g: ", ".join(g.sort_values("count", ascending=False)["skill_name"].head(top_n))
    ).rename("top_skills").reset_index()

    df_master = df_master.merge(top, left_on="user_id", right_on="user_id", how="left")
    # Si existía columna previa, preferimos la nueva (merge crea columna 'top_skills' y puede duplicar)
    if "top_skills_x" in df_master.columns and "top_skills_y" in df_master.columns:
        df_master["top_skills"] = df_master["top_skills_y"].fillna(df_master["top_skills_x"])
        df_master = df_master.drop(columns=["top_skills_x", "top_skills_y"])
    else:
        df_master["top_skills"] = df_master.get("top_skills", "").fillna("")

    df_master["top_skills"] = df_master["top_skills"].fillna("").astype(str)
    return df_master

# -------------------------
# Cache / persistencia simple
# -------------------------
def save_df_cache(df: pd.DataFrame, path: str):
    df_to_save = sanitize_dataframe_for_parquet(df)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    df_to_save.to_parquet(path, index=False)

def load_df_cache(path: str) -> pd.DataFrame:
    return pd.read_parquet(path)

# -------------------------
# Función principal de orquestación
# -------------------------
def build_all(db_name: str, mongo_uri: Optional[str] = None, cache_dir: str = "./cache") -> Dict[str, pd.DataFrame]:
    client = get_mongo_client(mongo_uri)
    collections = [
        "users","cvs","employabilities","cvs_skills","skills","applications",
        "courseenrollments","quizresults","userquizdatas","payments","notifications",
        "educations","companies"
    ]
    dfs = load_collections(client, db_name, collections)

    df_master = build_df_master(dfs)
    df_user_skills = build_df_user_skills(dfs)
    df_master = enrich_master_with_skills(df_master, df_user_skills, top_n=5)

    os.makedirs(cache_dir, exist_ok=True)
    save_df_cache(df_master, os.path.join(cache_dir, "df_master.parquet"))
    save_df_cache(df_user_skills, os.path.join(cache_dir, "df_user_skills.parquet"))

    sanitized_dfs = {k: sanitize_dataframe_for_parquet(v) for k, v in dfs.items()}
    return {"df_master": df_master, "df_user_skills": df_user_skills, **sanitized_dfs}

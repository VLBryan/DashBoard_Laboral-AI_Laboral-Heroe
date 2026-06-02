# app.py (ejemplo mínimo)
import streamlit as st
from data_loader import build_all, load_df_cache
import os

st.set_page_config(layout="wide", page_title="Laboral.AI - Dashboard")

@st.cache_data(ttl=3600)
def load_data(db_name, mongo_uri=None):
    # intenta cargar cache local primero
    cache_dir = "./cache"
    master_path = os.path.join(cache_dir, "df_master.parquet")
    skills_path = os.path.join(cache_dir, "df_user_skills.parquet")
    if os.path.exists(master_path) and os.path.exists(skills_path):
        return {"df_master": load_df_cache(master_path), "df_user_skills": load_df_cache(skills_path)}
    return build_all(db_name, mongo_uri, cache_dir)

data = load_data("nombre_de_tu_db", os.getenv("MONGO_URI"))
df_master = data["df_master"]
df_user_skills = data["df_user_skills"]

st.title("Laboral.AI - Postulantes")
st.metric("Total postulantes", len(df_master))
st.dataframe(df_master[["user_id","firstName","lastName","country","region","city","score","top_skills","is_laboral_hero"]].head(50))

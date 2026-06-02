# app.py (ejemplo mínimo)
import streamlit as st
from data_loader import build_all, load_df_cache
import os
from kpi_calculator import (
    compute_basic_kpis,
    compute_new_users_by_window,
    compute_application_kpis,
    compute_top_skills_coverage,
    compute_hero_comparison,
    compute_time_to_first_application,
    compute_time_series
)
from kpi_by_location import (
    compute_basic_kpis_by_location,
    compute_top_skills_by_location,
    compute_hero_vs_nonhero_by_location,
    compute_time_series_by_location,
    prepare_choropleth_df,
    compute_segment_kpis
)

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


#    ------ KPIs ------


data = load_data("nombre_de_tu_db")  # desde data_loader
df_master = data["df_master"]
df_user_skills = data["df_user_skills"]
df_apps = data.get("applications", None)

# KPIs
basic = compute_basic_kpis(df_master)
new_users = compute_new_users_by_window(df_master)
apps_kpis = compute_application_kpis(df_master)
top_skills = compute_top_skills_coverage(df_user_skills, df_master, top_n=10)
hero_cmp = compute_hero_comparison(df_master)
time_to_first = compute_time_to_first_application(df_master, df_apps)
ts = compute_time_series(df_master, df_apps, freq="W")

# Mostrar en Streamlit
st.metric("Total postulantes", basic["total_users"])
st.metric("Laboral Heroes", f'{basic["laboral_heroes_count"]} ({basic["pct_laboral_heroes"]:.1f}%)')
st.metric("Promedio employability score", f'{basic["avg_employability_score"]:.1f}')
st.dataframe(top_skills)
st.dataframe(hero_cmp)


#    ------ KPIs por ubicación ------


# df_master, df_user_skills, df_applications ya cargados
country_kpis = compute_basic_kpis_by_location(df_master, level="country")
st.dataframe(country_kpis.head(50))

top_skills_country = compute_top_skills_by_location(df_user_skills, df_master, level="country", top_n=10)
st.dataframe(top_skills_country)

hero_cmp_country = compute_hero_vs_nonhero_by_location(df_master, level="country")
st.dataframe(hero_cmp_country)

ts = compute_time_series_by_location(df_master, df_applications, level="country", freq="W")
st.line_chart(ts['users_ts'].pivot(index='createdAt', columns='country', values='new_users').fillna(0))

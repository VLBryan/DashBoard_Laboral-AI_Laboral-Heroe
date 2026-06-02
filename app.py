# app.py
import os
import streamlit as st
import pandas as pd
from datetime import datetime, timedelta

# importar módulos previos
from data_loader import build_all, load_df_cache
from kpi_calculator import (
    compute_basic_kpis, compute_new_users_by_window, compute_application_kpis,
    compute_top_skills_coverage, compute_hero_comparison, compute_time_series
)
from kpi_by_location import (
    compute_basic_kpis_by_location, compute_top_skills_by_location,
    compute_hero_vs_nonhero_by_location, compute_time_series_by_location,
    prepare_choropleth_df
)
from viz_factory import (
    choropleth_by_country, top_skills_bar, score_distribution,
    time_series_users, kpi_indicator, simple_funnel
)

# -------------------------
# Config
# -------------------------
st.set_page_config(layout="wide", page_title="Laboral.AI - Dashboard Postulantes")

DB_NAME = os.getenv("LABORAL_DB", "nombre_de_tu_db")
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
CACHE_DIR = "./cache"

# -------------------------
# Data loading (cached)
# -------------------------
@st.cache_data(ttl=600)
def load_data_cached(db_name: str, mongo_uri: str):
    # intenta cargar cache local; si no existe, build_all hará la extracción desde Mongo
    return build_all(db_name, mongo_uri, cache_dir=CACHE_DIR)

data_bundle = load_data_cached(DB_NAME, MONGO_URI)
df_master = data_bundle["df_master"]
df_user_skills = data_bundle["df_user_skills"]
df_applications = data_bundle.get("applications", pd.DataFrame())

# -------------------------
# Sidebar: filtros globales
# -------------------------
st.sidebar.header("Filtros globales")
# Fecha
max_date = pd.to_datetime(df_master['createdAt']).max() if 'createdAt' in df_master.columns else pd.Timestamp.now()
min_date = pd.to_datetime(df_master['createdAt']).min() if 'createdAt' in df_master.columns else (max_date - pd.Timedelta(days=365))
date_range = st.sidebar.date_input("Rango de registro", [min_date.date(), max_date.date()])

# Ubicación
countries = sorted(df_master['country'].dropna().unique().tolist()) if 'country' in df_master.columns else []
selected_countries = st.sidebar.multiselect("País", options=countries, default=countries[:5])

# Laboral Hero
hero_filter = st.sidebar.selectbox("Laboral Hero", options=["Todos", "Solo Heroes", "No Heroes"], index=0)

# Score slider
if 'score' in df_master.columns:
    min_score = int(pd.to_numeric(df_master['score'], errors='coerce').min(skipna=True) or 0)
    max_score = int(pd.to_numeric(df_master['score'], errors='coerce').max(skipna=True) or 100)
    score_range = st.sidebar.slider("Rango score", min_value=min_score, max_value=max_score, value=(min_score, max_score))
else:
    score_range = None

# Top N skills
top_n_skills = st.sidebar.slider("Top N skills (visual)", 5, 30, 12)

# Botón de recarga de cache (opcional)
if st.sidebar.button("Forzar recarga datos (ETL)"):
    # invalidar cache y recargar
    load_data_cached.clear()
    data_bundle = load_data_cached(DB_NAME, MONGO_URI)
    df_master = data_bundle["df_master"]
    df_user_skills = data_bundle["df_user_skills"]
    df_applications = data_bundle.get("applications", pd.DataFrame())
    st.sidebar.success("Datos recargados")

# -------------------------
# Aplicar filtros al df_master
# -------------------------
df = df_master.copy()
# fecha
start_dt = pd.to_datetime(date_range[0])
end_dt = pd.to_datetime(date_range[1]) + pd.Timedelta(days=1)
if 'createdAt' in df.columns:
    df = df[(pd.to_datetime(df['createdAt']) >= start_dt) & (pd.to_datetime(df['createdAt']) < end_dt)]
# country
if selected_countries:
    df = df[df['country'].isin(selected_countries)]
# laboral hero
if hero_filter == "Solo Heroes":
    df = df[df['is_laboral_hero'] == True]
elif hero_filter == "No Heroes":
    df = df[df['is_laboral_hero'] == False]
# score
if score_range and 'score' in df.columns:
    df['score'] = pd.to_numeric(df['score'], errors='coerce')
    df = df[(df['score'] >= score_range[0]) & (df['score'] <= score_range[1])]

# -------------------------
# KPIs principales (fila superior)
# -------------------------
basic = compute_basic_kpis(df)
apps_kpis = compute_application_kpis(df)
new_users = compute_new_users_by_window(df)

col1, col2, col3, col4, col5 = st.columns([1.2,1.2,1.2,1.2,1.2])
col1.plotly_chart(kpi_indicator(basic["total_users"], "Total postulantes"), use_container_width=True)
col2.plotly_chart(kpi_indicator(basic["laboral_heroes_count"], "Laboral Heroes"), use_container_width=True)
col3.plotly_chart(kpi_indicator(basic["avg_employability_score"] or 0, "Promedio score", fmt=".1f"), use_container_width=True)
col4.plotly_chart(kpi_indicator(apps_kpis["total_applications"], "Total aplicaciones"), use_container_width=True)
col5.metric("Nuevos 30d", new_users.get("new_users_30d", 0))

st.markdown("---")

# -------------------------
# Visuales principales (mapa + top skills + serie temporal)
# -------------------------
left, right = st.columns([2,1])

with left:
    st.subheader("Mapa de postulantes (por país)")
    # preparar df para choropleth (usa compute_basic_kpis_by_location)
    country_kpis = compute_basic_kpis_by_location(df_master, level="country")
    # si aplicaste filtros, recomputa por ubicación con compute_segment_kpis o filtra country_kpis
    # aquí usamos el df filtrado para mostrar solo países seleccionados
    country_kpis_filtered = country_kpis[country_kpis['country'].isin(df['country'].dropna().unique())] if 'country' in country_kpis.columns else country_kpis
    # prepara df_choro (necesitas map country->ISO en producción)
    df_choro = prepare_choropleth_df(country_kpis_filtered, level="country", metric="users_count")
    fig_map = choropleth_by_country(df_choro, location_col="geo_id", value_col="value", title="Concentración de postulantes")
    st.plotly_chart(fig_map, use_container_width=True, height=500)

with right:
    st.subheader("Top skills")
    top_skills_global = compute_top_skills_coverage(df_user_skills, df_master, top_n=top_n_skills)
    fig_top = top_skills_bar(top_skills_global, top_n=top_n_skills, title=f"Top {top_n_skills} skills")
    st.plotly_chart(fig_top, use_container_width=True)

st.markdown("---")

# Serie temporal
st.subheader("Evolución de registros (serie temporal)")
ts = compute_time_series(df_master, df_applications, freq="W")
users_ts = ts['users_ts']
if not users_ts.empty:
    fig_ts = time_series_users(users_ts, date_col='createdAt', value_col='new_users', title="Nuevos usuarios (semanal)")
    st.plotly_chart(fig_ts, use_container_width=True)
else:
    st.info("No hay datos temporales suficientes para mostrar la serie.")

st.markdown("---")

# -------------------------
# Tabla detalle (preview)
# -------------------------
st.subheader("Detalle de postulantes (preview)")
cols_to_show = ["user_id","firstName","lastName","country","region","city","score","top_skills","n_applications","is_laboral_hero"]
available = [c for c in cols_to_show if c in df.columns]
st.dataframe(df[available].sort_values("score", ascending=False).head(500))

# -------------------------
# Footer / notas
# -------------------------
st.markdown("**Notas:** Datos extraídos desde MongoDB; ajusta `MONGO_URI` y `DB_NAME` en variables de entorno.")

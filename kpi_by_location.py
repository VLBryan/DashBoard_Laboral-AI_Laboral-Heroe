# kpi_by_location.py
from typing import Tuple, Dict, Optional
import pandas as pd
import numpy as np

# -------------------------
# Utilidades internas
# -------------------------
def _ensure_location_cols(df: pd.DataFrame, level: str) -> pd.DataFrame:
    """
    Asegura que la columna de nivel exista en df.
    level: 'country' | 'region' | 'city' | cualquier columna existente
    """
    if level not in df.columns:
        df[level] = None
    return df

def _safe_numeric(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce")

# -------------------------
# KPI: agregados básicos por ubicación
# -------------------------
def compute_basic_kpis_by_location(df_master: pd.DataFrame, level: str = "country") -> pd.DataFrame:
    """
    Devuelve DataFrame con KPIs por ubicación (level):
      - users_count
      - active_count
      - laboral_heroes_count
      - pct_laboral_heroes
      - avg_score
      - median_score
      - avg_applications
    """
    df = df_master.copy()
    df = _ensure_location_cols(df, level)
    df['score_num'] = _safe_numeric(df.get('score', pd.Series([np.nan]*len(df))))
    grouped = df.groupby(level).agg(
        users_count = ('user_id', 'nunique'),
        active_count = ('isActive', lambda s: int(s.sum()) if s.dtype == 'bool' or s.dropna().shape[0] else int((s == True).sum()) if s.notna().any() else 0),
        laboral_heroes_count = ('is_laboral_hero', lambda s: int(s.sum())),
        avg_score = ('score_num', 'mean'),
        median_score = ('score_num', 'median'),
        avg_applications = ('n_applications', 'mean')
    ).reset_index()
    grouped['pct_laboral_heroes'] = grouped.apply(lambda r: (r['laboral_heroes_count'] / r['users_count'] * 100) if r['users_count'] else 0.0, axis=1)
    # ordenar por tamaño
    grouped = grouped.sort_values('users_count', ascending=False)
    return grouped

# -------------------------
# KPI: top skills por ubicación
# -------------------------
def compute_top_skills_by_location(df_user_skills: pd.DataFrame, df_master: pd.DataFrame, level: str = "country", top_n: int = 10) -> pd.DataFrame:
    """
    Devuelve top skills por ubicación:
      columns: [location, skill_name, users_with_skill, pct_users]
    df_user_skills: ['user_id','skill_name', ...]
    df_master must contain mapping user_id -> location level
    """
    if df_user_skills is None or df_user_skills.empty:
        return pd.DataFrame(columns=[level, "skill_name", "users_with_skill", "pct_users"])
    # map user -> location
    mapping = df_master[['user_id', level]].drop_duplicates()
    merged = df_user_skills.merge(mapping, left_on='user_id', right_on='user_id', how='left')
    merged[level] = merged[level].fillna("Unknown")
    total_by_loc = mapping.groupby(level)['user_id'].nunique().rename('total_users').reset_index()
    skill_counts = merged.groupby([level, 'skill_name'])['user_id'].nunique().rename('users_with_skill').reset_index()
    skill_counts = skill_counts.merge(total_by_loc, on=level, how='left')
    skill_counts['pct_users'] = skill_counts.apply(lambda r: (r['users_with_skill'] / r['total_users'] * 100) if r['total_users'] else 0.0, axis=1)
    # keep top_n per location
    skill_counts = skill_counts.sort_values([level, 'users_with_skill'], ascending=[True, False])
    top_per_loc = skill_counts.groupby(level).head(top_n).reset_index(drop=True)
    return top_per_loc

# -------------------------
# KPI: comparativa Hero vs No-Hero por ubicación
# -------------------------
def compute_hero_vs_nonhero_by_location(df_master: pd.DataFrame, level: str = "country") -> pd.DataFrame:
    """
    Devuelve métricas comparadas por ubicación y por is_laboral_hero:
      columns: [location, is_laboral_hero, users_count, avg_score, avg_applications]
    """
    df = df_master.copy()
    df = _ensure_location_cols(df, level)
    df['score_num'] = _safe_numeric(df.get('score', pd.Series([np.nan]*len(df))))
    df['is_laboral_hero'] = df['is_laboral_hero'].astype(bool)
    grouped = df.groupby([level, 'is_laboral_hero']).agg(
        users_count = ('user_id', 'nunique'),
        avg_score = ('score_num', 'mean'),
        avg_applications = ('n_applications', 'mean')
    ).reset_index()
    # pivot opcional para mostrar lado a lado
    pivot = grouped.pivot(index=level, columns='is_laboral_hero', values=['users_count','avg_score','avg_applications'])
    # flatten columns
    pivot.columns = ['{}_hero_{}'.format(col[0], 'yes' if col[1] else 'no') for col in pivot.columns]
    pivot = pivot.reset_index().fillna(0)
    return pivot

# -------------------------
# KPI: series temporales por ubicación
# -------------------------
def compute_time_series_by_location(df_master: pd.DataFrame, df_applications: Optional[pd.DataFrame] = None, level: str = "country", freq: str = "W") -> Dict[str, pd.DataFrame]:
    """
    Devuelve dict:
      - users_ts: DataFrame [location, period, new_users]
      - apps_ts: DataFrame [location, period, new_applications] (si df_applications provisto)
    period is the period start (datetime)
    """
    df = df_master.copy()
    df = _ensure_location_cols(df, level)
    df['createdAt'] = pd.to_datetime(df.get('createdAt', df.get('createdAt_user', pd.NaT)))
    # users ts
    users = df.dropna(subset=['createdAt']).copy()
    users = users.set_index('createdAt')
    users_ts = users.groupby(level).resample(freq).size().rename('new_users').reset_index()
    # apps ts
    apps_ts = pd.DataFrame()
    if df_applications is not None and not df_applications.empty:
        apps = df_applications.copy()
        apps['createdAt'] = pd.to_datetime(apps['createdAt'], errors='coerce')
        # map app.user -> location
        user_loc = df_master[['user_id', level]].drop_duplicates().rename(columns={'user_id':'user'})
        apps = apps.merge(user_loc, on='user', how='left')
        apps[level] = apps[level].fillna("Unknown")
        apps = apps.dropna(subset=['createdAt']).set_index('createdAt')
        apps_ts = apps.groupby(level).resample(freq).size().rename('new_applications').reset_index()
    return {"users_ts": users_ts, "apps_ts": apps_ts}

# -------------------------
# KPI: preparar dataframe para choropleth / mapa
# -------------------------
def prepare_choropleth_df(df_basic_by_loc: pd.DataFrame, level: str = "country", metric: str = "users_count", geo_map: Optional[Dict[str,str]] = None) -> pd.DataFrame:
    """
    Prepara df con columnas: [location, metric, geo_id]
    geo_map: optional mapping {location_name: geo_id} (ej. ISO country codes)
    Si no se provee geo_map, devuelve location y metric.
    """
    df = df_basic_by_loc.copy()
    df = df[[level, metric]].rename(columns={level: "location", metric: "value"})
    if geo_map:
        df['geo_id'] = df['location'].map(geo_map).fillna(df['location'])
    else:
        df['geo_id'] = df['location']
    return df[['location','geo_id','value']]

# -------------------------
# KPI: segmentación por ubicación y filtros combinados
# -------------------------
def compute_segment_kpis(df_master: pd.DataFrame, level: str = "country", filters: Optional[Dict] = None) -> pd.DataFrame:
    """
    Aplica filtros (dict) sobre df_master y devuelve basic_kpis_by_location.
    filters example: {"suggested_role": ["Data Scientist","Analyst"], "score_min": 70}
    """
    df = df_master.copy()
    if filters:
        for k, v in filters.items():
            if k == "score_min":
                df = df[pd.to_numeric(df.get('score', 0), errors='coerce') >= v]
            elif k == "score_max":
                df = df[pd.to_numeric(df.get('score', 0), errors='coerce') <= v]
            elif k == "suggested_role":
                df = df[df['suggested_role'].isin(v)]
            elif k == "is_laboral_hero":
                df = df[df['is_laboral_hero'] == bool(v)]
            else:
                if k in df.columns:
                    df = df[df[k].isin(v if isinstance(v, list) else [v])]
    return compute_basic_kpis_by_location(df, level=level)

# kpi_calculator.py
from typing import Tuple, Dict, Optional
import pandas as pd
import numpy as np

# -------------------------
# Helpers
# -------------------------
def safe_datetime(series: pd.Series) -> pd.Series:
    return pd.to_datetime(series, errors="coerce")

def percent(part: float, whole: float) -> float:
    return (part / whole * 100) if whole else 0.0

# -------------------------
# KPI: Totales y básicos
# -------------------------
def compute_basic_kpis(df_master: pd.DataFrame) -> Dict[str, float]:
    """
    Devuelve KPIs básicos:
      - total_users
      - active_users (isActive True)
      - laboral_heroes_count
      - pct_laboral_heroes
      - avg_employability_score (si existe)
      - median_employability_score
    """
    total = len(df_master)
    active = int(df_master['isActive'].sum()) if 'isActive' in df_master.columns else int(df_master.shape[0])
    heroes = int(df_master['is_laboral_hero'].sum()) if 'is_laboral_hero' in df_master.columns else 0

    # score safe
    score_col = 'score' if 'score' in df_master.columns else None
    if score_col:
        scores = pd.to_numeric(df_master[score_col], errors='coerce').dropna()
        avg_score = float(scores.mean()) if not scores.empty else np.nan
        med_score = float(scores.median()) if not scores.empty else np.nan
    else:
        avg_score = np.nan
        med_score = np.nan

    return {
        "total_users": total,
        "active_users": active,
        "laboral_heroes_count": heroes,
        "pct_laboral_heroes": percent(heroes, total),
        "avg_employability_score": avg_score,
        "median_employability_score": med_score
    }

# -------------------------
# KPI: Nuevos registros en ventanas temporales
# -------------------------
def compute_new_users_by_window(df_master: pd.DataFrame, as_of: Optional[pd.Timestamp] = None) -> Dict[str, int]:
    """
    Calcula nuevos usuarios en ventanas: 7, 30, 90 días.
    as_of: fecha de referencia (por defecto ahora)
    """
    if as_of is None:
        as_of = pd.Timestamp.now()
    created = safe_datetime(df_master.get("createdAt", df_master.get("createdAt_user", pd.Series([pd.NaT]*len(df_master)))))
    windows = {"7d": 7, "30d": 30, "90d": 90}
    out = {}
    for k, days in windows.items():
        cutoff = as_of - pd.Timedelta(days=days)
        out[f"new_users_{k}"] = int((created >= cutoff).sum())
    return out

# -------------------------
# KPI: Aplicaciones y tasa de aplicación
# -------------------------
def compute_application_kpis(df_master: pd.DataFrame) -> Dict[str, float]:
    """
    Requiere columna 'n_applications' en df_master.
    Devuelve:
      - total_applications
      - avg_applications_per_user
      - pct_users_with_application
    """
    if 'n_applications' not in df_master.columns:
        return {"total_applications": 0, "avg_applications_per_user": 0.0, "pct_users_with_application": 0.0}
    total_apps = int(df_master['n_applications'].sum())
    avg_apps = float(df_master['n_applications'].mean())
    users_with_apps = int((df_master['n_applications'] > 0).sum())
    pct_users_with_apps = percent(users_with_apps, len(df_master))
    return {
        "total_applications": total_apps,
        "avg_applications_per_user": avg_apps,
        "pct_users_with_application": pct_users_with_apps
    }

# -------------------------
# KPI: Top skills y cobertura
# -------------------------
def compute_top_skills_coverage(df_user_skills: pd.DataFrame, df_master: pd.DataFrame, top_n: int = 10) -> pd.DataFrame:
    """
    Devuelve DataFrame con columnas:
      - skill_name
      - users_with_skill
      - pct_users
    df_user_skills expected columns: ['user_id', 'skill_name', 'count']
    """
    if df_user_skills is None or df_user_skills.empty:
        return pd.DataFrame(columns=["skill_name", "users_with_skill", "pct_users"])
    total_users = len(df_master)
    # contar usuarios únicos por skill
    skill_counts = df_user_skills.groupby("skill_name")["user_id"].nunique().reset_index().rename(columns={"user_id": "users_with_skill"})
    skill_counts["pct_users"] = skill_counts["users_with_skill"].apply(lambda x: percent(x, total_users))
    skill_counts = skill_counts.sort_values("users_with_skill", ascending=False).head(top_n)
    return skill_counts

# -------------------------
# KPI: Comparativa Laboral Hero vs No-Hero
# -------------------------
def compute_hero_comparison(df_master: pd.DataFrame, metric_cols: Optional[list] = None) -> pd.DataFrame:
    """
    Agrupa por is_laboral_hero y calcula métricas agregadas:
      - count, avg_score, median_score, avg_applications
    """
    if metric_cols is None:
        metric_cols = ["score", "n_applications"]
    df = df_master.copy()
    df["is_laboral_hero"] = df["is_laboral_hero"].astype(bool)
    agg = {}
    agg["count"] = ("user_id", "nunique")
    if "score" in df.columns:
        agg["avg_score"] = ("score", lambda s: pd.to_numeric(s, errors="coerce").mean())
        agg["median_score"] = ("score", lambda s: pd.to_numeric(s, errors="coerce").median())
    if "n_applications" in df.columns:
        agg["avg_applications"] = ("n_applications", "mean")
    grouped = df.groupby("is_laboral_hero").agg(**agg).reset_index()
    # format
    grouped["avg_score"] = grouped["avg_score"].astype(float)
    grouped["median_score"] = grouped["median_score"].astype(float)
    grouped["avg_applications"] = grouped["avg_applications"].astype(float)
    return grouped

# -------------------------
# KPI: Time to first application
# -------------------------
def compute_time_to_first_application(df_master: pd.DataFrame, df_applications: Optional[pd.DataFrame] = None) -> Dict[str, float]:
    """
    Si se provee df_applications (con columnas 'user' y 'createdAt'), calcula:
      - median_days_to_first_application
      - mean_days_to_first_application
    Si no, intenta usar columnas en df_master: 'first_application_at' si existe.
    """
    if df_applications is not None and not df_applications.empty:
        apps = df_applications.copy()
        apps['createdAt'] = safe_datetime(apps['createdAt'])
        first_apps = apps.sort_values('createdAt').groupby('user').first().reset_index()
        # merge with users createdAt
        users = df_master[['user_id', 'createdAt']].copy()
        users['createdAt'] = safe_datetime(users['createdAt'])
        merged = first_apps.merge(users, left_on='user', right_on='user_id', how='left', suffixes=('_app','_user'))
        merged['delta_days'] = (merged['createdAt_app'] - merged['createdAt']).dt.total_seconds() / (3600*24)
        merged = merged[merged['delta_days'].notna() & (merged['delta_days'] >= 0)]
        return {
            "median_days_to_first_application": float(merged['delta_days'].median()) if not merged.empty else np.nan,
            "mean_days_to_first_application": float(merged['delta_days'].mean()) if not merged.empty else np.nan
        }
    # fallback: try df_master column
    if 'first_application_at' in df_master.columns:
        first = safe_datetime(df_master['first_application_at'])
        created = safe_datetime(df_master['createdAt'])
        delta = (first - created).dt.total_seconds() / (3600*24)
        delta = delta[delta.notna() & (delta >= 0)]
        return {
            "median_days_to_first_application": float(delta.median()) if not delta.empty else np.nan,
            "mean_days_to_first_application": float(delta.mean()) if not delta.empty else np.nan
        }
    return {"median_days_to_first_application": np.nan, "mean_days_to_first_application": np.nan}

# -------------------------
# KPI: Series temporal de registros y aplicaciones
# -------------------------
def compute_time_series(df_master: pd.DataFrame, df_applications: Optional[pd.DataFrame] = None, freq: str = "W") -> Dict[str, pd.DataFrame]:
    """
    Devuelve dict con:
      - users_ts: series de nuevos usuarios por freq
      - apps_ts: series de nuevas aplicaciones por freq (si df_applications provisto)
    freq examples: 'D', 'W', 'M'
    """
    users = df_master.copy()
    users['createdAt'] = safe_datetime(users.get('createdAt', users.get('createdAt_user', pd.NaT)))
    users_ts = users.set_index('createdAt').resample(freq).size().rename("new_users").reset_index() if users['createdAt'].notna().any() else pd.DataFrame(columns=['createdAt','new_users'])

    apps_ts = pd.DataFrame()
    if df_applications is not None and not df_applications.empty:
        apps = df_applications.copy()
        apps['createdAt'] = safe_datetime(apps['createdAt'])
        apps_ts = apps.set_index('createdAt').resample(freq).size().rename("new_applications").reset_index()
    return {"users_ts": users_ts, "apps_ts": apps_ts}

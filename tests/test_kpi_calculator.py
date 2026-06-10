# tests/test_kpi_calculator.py
import pandas as pd
import numpy as np
import pytest

from src.kpi_calculator import (
    percent,
    compute_basic_kpis,
    compute_application_kpis,
    compute_top_skills_coverage,
    compute_hero_comparison,
    compute_time_series,
)


def test_percent():
    assert percent(1, 4) == 25.0
    assert percent(0, 0) == 0.0


def test_compute_basic_kpis(df_master):
    kpis = compute_basic_kpis(df_master)
    assert kpis["total_users"] == 10
    assert kpis["active_users"] == 7
    assert kpis["laboral_heroes_count"] == 3
    assert kpis["pct_laboral_heroes"] == 30.0
    assert kpis["avg_employability_score"] == pytest.approx(70.0)


def test_compute_basic_kpis_empty():
    kpis = compute_basic_kpis(pd.DataFrame())
    assert kpis["total_users"] == 0
    assert kpis["laboral_heroes_count"] == 0
    assert np.isnan(kpis["avg_employability_score"])


def test_compute_application_kpis(df_master):
    kpis = compute_application_kpis(df_master)
    assert kpis["total_applications"] == 16
    assert kpis["pct_users_with_application"] == 60.0


def test_compute_application_kpis_missing_column():
    kpis = compute_application_kpis(pd.DataFrame({"user_id": ["1", "2"]}))
    assert kpis == {"total_applications": 0, "avg_applications_per_user": 0.0, "pct_users_with_application": 0.0}


def test_compute_top_skills_coverage(df_master, df_user_skills):
    result = compute_top_skills_coverage(df_user_skills, df_master, top_n=10)
    python_row = result[result["skill_name"] == "Python"].iloc[0]
    assert python_row["users_with_skill"] == 3
    assert python_row["pct_users"] == pytest.approx(30.0)


def test_compute_top_skills_coverage_empty(df_master):
    result = compute_top_skills_coverage(pd.DataFrame(), df_master)
    assert list(result.columns) == ["skill_name", "users_with_skill", "pct_users"]
    assert result.empty


def test_compute_hero_comparison(df_master):
    result = compute_hero_comparison(df_master)
    heroes = result[result["is_laboral_hero"] == True].iloc[0]
    non_heroes = result[result["is_laboral_hero"] == False].iloc[0]
    assert heroes["count"] == 3
    assert non_heroes["count"] == 7


def test_compute_time_series(df_master, df_applications):
    ts = compute_time_series(df_master, df_applications, freq="W")
    assert "users_ts" in ts and "apps_ts" in ts
    assert not ts["users_ts"].empty
    assert ts["apps_ts"]["new_applications"].sum() == 4

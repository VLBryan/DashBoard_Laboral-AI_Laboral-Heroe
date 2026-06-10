# tests/test_kpi_by_location.py
import pandas as pd

from src.kpi_by_location import (
    compute_basic_kpis_by_location,
    compute_hero_vs_nonhero_by_location,
    prepare_choropleth_df,
)


def test_compute_basic_kpis_by_location(df_master):
    result = compute_basic_kpis_by_location(df_master, level="country")
    peru = result[result["country"] == "Peru"].iloc[0]
    chile = result[result["country"] == "Chile"].iloc[0]
    assert peru["users_count"] == 5
    assert chile["users_count"] == 5
    assert peru["laboral_heroes_count"] == 1
    assert chile["laboral_heroes_count"] == 2


def test_compute_hero_vs_nonhero_by_location(df_master):
    result = compute_hero_vs_nonhero_by_location(df_master, level="country")
    peru = result[result["country"] == "Peru"].iloc[0]
    assert peru["users_count_hero_yes"] == 1
    assert peru["users_count_hero_no"] == 4


def test_prepare_choropleth_df(df_master):
    basic = compute_basic_kpis_by_location(df_master, level="country")
    choro = prepare_choropleth_df(basic, level="country", metric="users_count")
    assert list(choro.columns) == ["location", "geo_id", "value"]
    assert set(choro["location"]) == {"Peru", "Chile"}


def test_prepare_choropleth_df_with_geo_map(df_master):
    basic = compute_basic_kpis_by_location(df_master, level="country")
    geo_map = {"Peru": "PER", "Chile": "CHL"}
    choro = prepare_choropleth_df(basic, level="country", metric="users_count", geo_map=geo_map)
    mapping = dict(zip(choro["location"], choro["geo_id"]))
    assert mapping["Peru"] == "PER"
    assert mapping["Chile"] == "CHL"

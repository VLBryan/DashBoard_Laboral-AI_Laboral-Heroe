# tests/test_data_loader.py
import pandas as pd
from bson import ObjectId

from src.data_loader import (
    sanitize_dataframe_for_parquet,
    normalize_location,
    explode_list_field,
    normalize_colnames,
)


def test_sanitize_dataframe_for_parquet():
    df = pd.DataFrame({
        "id": [ObjectId(), ObjectId()],
        "meta": [{"a": 1}, {"b": 2}],
        "tags": [["python", "sql"], ["excel"]],
        "raw": [b"hello", b"world"],
        "name": ["Ana", "Luis"],
    })
    out = sanitize_dataframe_for_parquet(df)
    assert all(isinstance(v, str) for v in out["id"])
    assert all(isinstance(v, str) for v in out["meta"])
    assert all(isinstance(v, str) for v in out["tags"])
    assert out["raw"].tolist() == ["hello", "world"]
    assert out["name"].tolist() == ["Ana", "Luis"]


def test_sanitize_dataframe_for_parquet_empty():
    assert sanitize_dataframe_for_parquet(pd.DataFrame()).empty


def test_normalize_location_dict():
    df = pd.DataFrame({"location": [{"country": "Peru", "region": "Lima", "city": "Miraflores"}]})
    out = normalize_location(df)
    assert out.loc[0, "country"] == "Peru"
    assert out.loc[0, "region"] == "Lima"
    assert out.loc[0, "city"] == "Miraflores"


def test_normalize_location_string():
    df = pd.DataFrame({"location": ["Peru/Lima/Miraflores", "Chile"]})
    out = normalize_location(df)
    assert out.loc[0, ["country", "region", "city"]].tolist() == ["Peru", "Lima", "Miraflores"]
    assert out.loc[1, "country"] == "Chile"
    assert pd.isna(out.loc[1, "region"])


def test_explode_list_field():
    df = pd.DataFrame({"user_id": ["1", "2"], "skills": [["Python", "SQL"], "Excel"]})
    out = explode_list_field(df, "user_id", "skills", "skill")
    assert set(out[out["user_id"] == "1"]["skill"]) == {"Python", "SQL"}
    assert set(out[out["user_id"] == "2"]["skill"]) == {"Excel"}


def test_explode_list_field_missing_column():
    df = pd.DataFrame({"user_id": ["1"]})
    out = explode_list_field(df, "user_id", "skills", "skill")
    assert list(out.columns) == ["user_id", "skill"]
    assert out.empty


def test_normalize_colnames():
    df = pd.DataFrame(columns=["First Name", "e-mail", "Score (0-100)"])
    out = normalize_colnames(df)
    assert list(out.columns) == ["first_name", "email", "score_0100"]

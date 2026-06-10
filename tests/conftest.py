# tests/conftest.py
import pandas as pd
import pytest


@pytest.fixture
def df_master():
    return pd.DataFrame({
        "user_id": [str(i) for i in range(1, 11)],
        "isActive": [True, True, False, True, True, False, True, True, True, False],
        "is_laboral_hero": [True, False, False, True, False, False, True, False, False, False],
        "score": [80, 60, None, 90, 70, 50, 85, 65, 75, 55],
        "n_applications": [3, 0, 1, 5, 0, 2, 4, 0, 1, 0],
        "createdAt": pd.to_datetime([
            "2024-01-01", "2024-01-02", "2024-01-03", "2024-01-04", "2024-01-05",
            "2024-02-01", "2024-02-02", "2024-02-03", "2024-02-04", "2024-02-05",
        ]),
        "country": ["Peru", "Peru", "Peru", "Chile", "Chile", "Peru", "Chile", "Chile", "Peru", "Chile"],
        "region": ["Lima", "Lima", "Cusco", "Santiago", "Santiago", "Lima", "Santiago", "Santiago", "Cusco", "Santiago"],
        "top_skills": ["Python, SQL"] * 10,
    })


@pytest.fixture
def df_user_skills():
    rows = []
    skills_by_user = {
        "1": ["Python", "SQL", "Excel"],
        "2": ["Python"],
        "3": ["SQL"],
        "4": ["Python", "Excel"],
        "5": ["Excel"],
    }
    for user_id, skills in skills_by_user.items():
        for skill in skills:
            rows.append({"user_id": user_id, "skill_name": skill, "count": 1})
    return pd.DataFrame(rows)


@pytest.fixture
def df_applications():
    return pd.DataFrame({
        "user": ["1", "1", "2", "3"],
        "createdAt": pd.to_datetime([
            "2024-01-10", "2024-01-15", "2024-02-10", "2024-02-15",
        ]),
    })

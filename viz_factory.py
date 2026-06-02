# viz_factory.py
from typing import Optional, List, Dict
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import altair as alt

# -------------------------
# 1) Choropleth / mapa por país (Plotly)
# -------------------------
def choropleth_by_country(df_choro: pd.DataFrame,
                          location_col: str = "geo_id",
                          value_col: str = "value",
                          hover_cols: Optional[List[str]] = None,
                          title: str = "Postulantes por país",
                          color_scale: str = "Blues") -> go.Figure:
    """
    df_choro: DataFrame con columnas ['location','geo_id','value'] (geo_id = ISO country code preferred)
    Devuelve: plotly.graph_objects.Figure (choropleth)
    """
    hover_cols = hover_cols or []
    hover_data = {c: True for c in hover_cols}
    fig = px.choropleth(df_choro,
                        locations=location_col,
                        color=value_col,
                        hover_name="location",
                        hover_data=hover_data,
                        color_continuous_scale=color_scale,
                        projection="natural earth",
                        title=title)
    fig.update_layout(margin=dict(l=0,r=0,t=40,b=0), coloraxis_colorbar=dict(title=value_col))
    return fig

# -------------------------
# 2) Top N skills (barra horizontal, Plotly)
# -------------------------
def top_skills_bar(df_skills: pd.DataFrame,
                   skill_col: str = "skill_name",
                   count_col: str = "users_with_skill",
                   top_n: int = 10,
                   title: str = "Top skills") -> go.Figure:
    """
    df_skills: DataFrame with skill_name, users_with_skill, pct_users (global or per-location)
    """
    df = df_skills.sort_values(count_col, ascending=False).head(top_n)
    fig = px.bar(df, x=count_col, y=skill_col, orientation='h', text=count_col, title=title)
    fig.update_layout(yaxis={'categoryorder':'total ascending'}, margin=dict(l=120,t=40))
    fig.update_traces(texttemplate='%{text}', textposition='outside')
    return fig

# -------------------------
# 3) Distribución de scores (histograma + boxplot combinado, Plotly)
# -------------------------
def score_distribution(df_master: pd.DataFrame,
                       score_col: str = "score",
                       bins: int = 20,
                       title: str = "Distribución de employability score") -> go.Figure:
    """
    Devuelve figura con histograma y boxplot superior para inspección rápida.
    """
    df = df_master.copy()
    df[score_col] = pd.to_numeric(df.get(score_col), errors='coerce')
    hist = px.histogram(df, x=score_col, nbins=bins, title=title, marginal="box", opacity=0.8)
    hist.update_layout(margin=dict(l=40,r=20,t=40,b=40))
    return hist

# -------------------------
# 4) Serie temporal de registros (Plotly line)
# -------------------------
def time_series_users(df_ts: pd.DataFrame,
                      date_col: str = "createdAt",
                      value_col: str = "new_users",
                      group_col: Optional[str] = None,
                      title: str = "Nuevos usuarios en el tiempo",
                      freq_label: Optional[str] = None) -> go.Figure:
    """
    df_ts: DataFrame con columnas [date_col, value_col] o [group_col, date_col, value_col]
    Si group_col provisto, crea líneas por grupo.
    """
    if group_col and group_col in df_ts.columns:
        fig = px.line(df_ts, x=date_col, y=value_col, color=group_col, title=title)
    else:
        fig = px.line(df_ts, x=date_col, y=value_col, title=title)
    fig.update_layout(xaxis_title=f"{freq_label or 'Fecha'}", yaxis_title="Nuevos usuarios", margin=dict(t=40))
    return fig

# -------------------------
# 5) Funnel simple (registro -> CV -> aplicación -> contratación) (Plotly)
# -------------------------
def simple_funnel(steps: Dict[str, int], title: str = "Funnel de conversión") -> go.Figure:
    """
    steps: dict ordenado {"Registrados": 1000, "CV completado": 800, "Aplicaron": 300, "Contratados": 20}
    Devuelve: funnel chart (plotly)
    """
    labels = list(steps.keys())
    values = list(steps.values())
    fig = go.Figure(go.Funnel(y=labels, x=values, textinfo="value+percent initial"))
    fig.update_layout(title=title, margin=dict(l=20,r=20,t=40,b=20))
    return fig

# -------------------------
# 6) Heatmap de match score por puesto vs skill cluster (Plotly)
# -------------------------
def match_heatmap(df_matches: pd.DataFrame,
                  x_col: str = "job_title",
                  y_col: str = "skill_cluster",
                  value_col: str = "avg_score",
                  top_n_x: int = 20,
                  top_n_y: int = 20,
                  title: str = "Heatmap de match score") -> go.Figure:
    """
    df_matches: aggregated DataFrame with job_title, skill_cluster, avg_score
    Se limita a top_n en cada eje para legibilidad.
    """
    top_x = df_matches.groupby(x_col)[value_col].mean().nlargest(top_n_x).index
    top_y = df_matches.groupby(y_col)[value_col].mean().nlargest(top_n_y).index
    df = df_matches[df_matches[x_col].isin(top_x) & df_matches[y_col].isin(top_y)]
    pivot = df.pivot_table(index=y_col, columns=x_col, values=value_col, aggfunc='mean').fillna(0)
    fig = px.imshow(pivot, labels=dict(x="Puesto", y="Skill cluster", color=value_col), aspect="auto", title=title)
    fig.update_layout(margin=dict(l=120,t=40,b=80))
    return fig

# -------------------------
# 7) Tabla interactiva (Altair) para detalle por usuario (paginable en Streamlit)
# -------------------------
def altair_user_table(df_master: pd.DataFrame,
                      columns: Optional[List[str]] = None,
                      max_rows: int = 1000,
                      title: str = "Detalle de postulantes") -> alt.Chart:
    """
    Devuelve un objeto Altair con tabla simple (scrollable en Streamlit).
    Nota: Altair no es ideal para tablas complejas; para tablas ricas usar AgGrid en Streamlit.
    """
    cols = columns or ["user_id","firstName","lastName","country","region","city","score","top_skills","is_laboral_hero"]
    df = df_master[cols].fillna("").head(max_rows)
    # convertir a formato largo para Altair table rendering
    chart = alt.Chart(df.reset_index()).mark_text().encode(
        x=alt.X('index:O', axis=None),
        y=alt.Y('row_number:O', axis=None)
    )
    # Simpler: return a basic table using altair's transform_fold
    table = alt.Chart(df).transform_window(
        row_number='row_number()'
    ).transform_fold(
        cols
    ).mark_text().encode(
        y=alt.Y('row_number:O', axis=None),
        text='value:N',
        column=alt.Column('key:N', header=alt.Header(labelAngle=-45, labelOrient='bottom'))
    ).properties(title=title)
    return table

# -------------------------
# 8) KPI cards (Plotly indicator) para Streamlit
# -------------------------
def kpi_indicator(value: float, title: str, delta: Optional[float] = None, fmt: str = ".0f") -> go.Figure:
    """
    Devuelve un indicador Plotly (single KPI) con delta opcional.
    """
    fig = go.Figure()
    fig.add_trace(go.Indicator(
        mode="number+delta" if delta is not None else "number",
        value=value,
        number={'valueformat': fmt},
        delta={'reference': delta} if delta is not None else None,
        title={'text': title}
    ))
    fig.update_layout(margin=dict(l=10,r=10,t=20,b=10), height=120)
    return fig

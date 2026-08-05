"""
app.py
Dashboard Streamlit - Plateforme décisionnelle Oil & Gas
Connexion directe à PostgreSQL (dw_oil_gas)
"""

import os
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st
from dotenv import load_dotenv
from sqlalchemy import create_engine

# ---------- Config page ----------
st.set_page_config(
    page_title="Oil & Gas Analytics",
    page_icon="🛢️",
    layout="wide",
)

# ---------- Connexion PostgreSQL ----------
# En local : lit le fichier .env
# Sur Streamlit Cloud : lit st.secrets (configuré dans Advanced settings > Secrets)
load_dotenv(Path(__file__).resolve().parent / ".env")


def get_config(key: str, default: str = "") -> str:
    try:
        if key in st.secrets:
            return st.secrets[key]
    except Exception:
        pass  # pas de secrets.toml en local, c'est normal
    return os.getenv(key, default)


PG_HOST = get_config("POSTGRES_HOST", "localhost")
PG_PORT = get_config("POSTGRES_PORT", "5432")
PG_DB = get_config("POSTGRES_DB", "dw_oil_gas")
PG_USER = get_config("POSTGRES_USER", "postgres")
PG_PASSWORD = get_config("POSTGRES_PASSWORD", "postgres")


@st.cache_resource
def get_engine():
    url = f"postgresql+psycopg2://{PG_USER}:{PG_PASSWORD}@{PG_HOST}:{PG_PORT}/{PG_DB}"
    return create_engine(url)


@st.cache_data(ttl=300)
def load_data():
    engine = get_engine()

    fact_production = pd.read_sql(
        """
        SELECT fp.*, dw.field_id, df.field_name, dt.year, dt.month, dt.quarter
        FROM fact_production fp
        JOIN dim_well dw ON fp.well_id = dw.well_id
        JOIN dim_field df ON dw.field_id = df.field_id
        JOIN dim_time dt ON fp.date_id = dt.date_id
        """,
        engine,
    )

    fact_maintenance = pd.read_sql(
        """
        SELECT fm.*, de.equipment_type, de.field_id, df.field_name
        FROM fact_maintenance fm
        JOIN dim_equipment de ON fm.equipment_id = de.equipment_id
        JOIN dim_field df ON de.field_id = df.field_id
        """,
        engine,
    )

    fact_sales = pd.read_sql(
        """
        SELECT fs.*, df.field_name, dt.year, dt.month
        FROM fact_sales fs
        JOIN dim_field df ON fs.field_id = df.field_id
        JOIN dim_time dt ON fs.date_id = dt.date_id
        """,
        engine,
    )

    dim_field = pd.read_sql("SELECT * FROM dim_field", engine)

    return fact_production, fact_maintenance, fact_sales, dim_field


fact_production, fact_maintenance, fact_sales, dim_field = load_data()

# ---------- Sidebar : filtres ----------
st.sidebar.title("🛢️ Oil & Gas Analytics")
st.sidebar.markdown("---")

fields_options = ["Tous"] + sorted(dim_field.field_name.unique().tolist())
selected_field = st.sidebar.selectbox("Champ pétrolier", fields_options)

years_options = sorted(fact_production.year.unique().tolist())
selected_years = st.sidebar.multiselect("Années", years_options, default=years_options)

if st.sidebar.button("🔄 Rafraîchir les données"):
    st.cache_data.clear()
    st.rerun()

# ---------- Filtrage ----------
prod = fact_production[fact_production.year.isin(selected_years)]
maint = fact_maintenance.copy()
sales = fact_sales[fact_sales.year.isin(selected_years)]

if selected_field != "Tous":
    prod = prod[prod.field_name == selected_field]
    maint = maint[maint.field_name == selected_field]
    sales = sales[sales.field_name == selected_field]

# ---------- KPIs ----------
st.title("Dashboard Production & Exploitation")

col1, col2, col3, col4 = st.columns(4)

total_production = prod.barrels_extracted.sum()
total_revenue = sales.revenue.sum()
avg_cost_per_barrel = prod.cost.sum() / total_production if total_production else 0
total_downtime = maint.downtime_hours.sum()

col1.metric("Production totale (barils)", f"{total_production:,.0f}")
col2.metric("Chiffre d'affaires", f"${total_revenue:,.0f}")
col3.metric("Coût moyen / baril", f"${avg_cost_per_barrel:,.2f}")
col4.metric("Temps d'arrêt total (h)", f"{total_downtime:,.0f}")

st.markdown("---")

# ---------- Production par champ / mois ----------
c1, c2 = st.columns(2)

with c1:
    st.subheader("Production mensuelle")
    monthly = prod.groupby(["year", "month"], as_index=False).barrels_extracted.sum()
    monthly["period"] = monthly.year.astype(str) + "-" + monthly.month.astype(str).str.zfill(2)
    fig = px.line(monthly, x="period", y="barrels_extracted", markers=True)
    fig.update_layout(xaxis_title="Période", yaxis_title="Barils extraits")
    st.plotly_chart(fig, use_container_width=True)

with c2:
    st.subheader("Production par champ")
    by_field = prod.groupby("field_name", as_index=False).barrels_extracted.sum()
    fig = px.bar(by_field, x="field_name", y="barrels_extracted", color="field_name")
    fig.update_layout(xaxis_title="Champ", yaxis_title="Barils extraits", showlegend=False)
    st.plotly_chart(fig, use_container_width=True)

# ---------- Maintenance ----------
c3, c4 = st.columns(2)

with c3:
    st.subheader("Pannes par type d'équipement")
    by_equip = maint.groupby("equipment_type", as_index=False).agg(
        nb_pannes=("maintenance_id", "count"),
        downtime=("downtime_hours", "sum"),
    )
    fig = px.bar(by_equip, x="equipment_type", y="nb_pannes", color="equipment_type")
    fig.update_layout(xaxis_title="Type d'équipement", yaxis_title="Nombre de pannes", showlegend=False)
    st.plotly_chart(fig, use_container_width=True)

with c4:
    st.subheader("Coût de maintenance par type de panne")
    by_failure = maint.groupby("failure_type", as_index=False).cost.sum()
    fig = px.pie(by_failure, names="failure_type", values="cost")
    st.plotly_chart(fig, use_container_width=True)

# ---------- Ventes ----------
st.markdown("---")
st.subheader("Ventes par type de produit")

c5, c6 = st.columns(2)

with c5:
    by_product = sales.groupby("product_type", as_index=False).revenue.sum()
    fig = px.bar(by_product, x="product_type", y="revenue", color="product_type")
    fig.update_layout(xaxis_title="Produit", yaxis_title="Chiffre d'affaires ($)", showlegend=False)
    st.plotly_chart(fig, use_container_width=True)

with c6:
    monthly_sales = sales.groupby(["year", "month"], as_index=False).revenue.sum()
    monthly_sales["period"] = monthly_sales.year.astype(str) + "-" + monthly_sales.month.astype(str).str.zfill(2)
    fig = px.line(monthly_sales, x="period", y="revenue", markers=True)
    fig.update_layout(xaxis_title="Période", yaxis_title="Chiffre d'affaires ($)")
    st.plotly_chart(fig, use_container_width=True)

# ---------- Table détaillée ----------
st.markdown("---")
with st.expander("Voir les données de production détaillées"):
    st.dataframe(prod.sort_values("date_id", ascending=False), use_container_width=True)
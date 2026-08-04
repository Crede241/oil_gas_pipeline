"""
transform.py
Construit les tables dimensions et faits, prêtes à être chargées dans PostgreSQL.
"""

import pandas as pd


def build_dim_time(all_dates: pd.Series) -> pd.DataFrame:
    """Construit dim_time à partir de toutes les dates rencontrées dans le projet."""
    unique_dates = pd.to_datetime(all_dates.dropna().unique())
    dim_time = pd.DataFrame({"date_id": unique_dates})
    dim_time["day"] = dim_time.date_id.dt.day
    dim_time["month"] = dim_time.date_id.dt.month
    dim_time["quarter"] = dim_time.date_id.dt.quarter
    dim_time["year"] = dim_time.date_id.dt.year
    dim_time["week"] = dim_time.date_id.dt.isocalendar().week
    return dim_time.sort_values("date_id").reset_index(drop=True)


def transform(cleaned: dict[str, pd.DataFrame]) -> dict[str, pd.DataFrame]:
    fields = cleaned["fields"]
    wells = cleaned["wells"]
    equipment = cleaned["equipment"]
    employees = cleaned["employees"]
    production = cleaned["production"].copy()
    maintenance = cleaned["maintenance"].copy()
    sales = cleaned["sales"].copy()

    # ---------- Dimensions (renommage direct, déjà propres) ----------
    dim_field = fields.rename(columns={})
    dim_well = wells.rename(columns={})
    dim_equipment = equipment.rename(columns={})
    dim_employee = employees.rename(columns={})

    # ---------- dim_time à partir de toutes les dates utilisées ----------
    all_dates = pd.concat([production["date"], maintenance["date"], sales["date"]])
    dim_time = build_dim_time(all_dates)

    # ---------- fact_production ----------
    production["date_id"] = pd.to_datetime(production["date"]).dt.date
    production["cost_per_barrel"] = (
        production["cost"] / production["barrels_extracted"].replace(0, pd.NA)
    ).round(4)
    fact_production = production[
        ["production_id", "well_id", "date_id", "barrels_extracted", "cost", "cost_per_barrel"]
    ]

    # ---------- fact_maintenance ----------
    maintenance["date_id"] = pd.to_datetime(maintenance["date"]).dt.date
    fact_maintenance = maintenance[
        ["maintenance_id", "equipment_id", "date_id", "failure_type", "downtime_hours", "cost"]
    ]

    # ---------- fact_sales ----------
    sales["date_id"] = pd.to_datetime(sales["date"]).dt.date
    fact_sales = sales[
        ["sale_id", "date_id", "field_id", "product_type", "quantity_barrels",
         "price_per_barrel", "revenue"]
    ]

    return {
        "dim_time": dim_time,
        "dim_field": dim_field,
        "dim_well": dim_well,
        "dim_equipment": dim_equipment,
        "dim_employee": dim_employee,
        "fact_production": fact_production,
        "fact_maintenance": fact_maintenance,
        "fact_sales": fact_sales,
    }


if __name__ == "__main__":
    from extract import extract
    from clean import clean

    data = extract()
    cleaned_data = clean(data)
    transformed = transform(cleaned_data)
    for name, df in transformed.items():
        print(name, df.shape)

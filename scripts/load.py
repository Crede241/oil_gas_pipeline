"""
load.py
Charge les tables transformées dans PostgreSQL (base dw_oil_gas).
Respecte l'ordre dimensions -> faits pour ne pas casser les clés étrangères.
"""

import os
from pathlib import Path

import pandas as pd
from sqlalchemy import create_engine
from dotenv import load_dotenv
from urllib.parse import quote_plus

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

PG_HOST = os.getenv("POSTGRES_HOST", "localhost")
PG_PORT = os.getenv("POSTGRES_PORT", "5432")
PG_DB = os.getenv("POSTGRES_DB", "dw_oil_gas")
PG_USER = os.getenv("POSTGRES_USER", "postgres")
PG_PASSWORD = os.getenv("POSTGRES_PASSWORD", "postgres")

# Ordre important : dimensions d'abord, puis faits (contraintes de clés étrangères)
LOAD_ORDER = [
    "dim_time",
    "dim_field",
    "dim_well",
    "dim_equipment",
    "dim_employee",
    "fact_production",
    "fact_maintenance",
    "fact_sales",
]


def get_engine():
    user = quote_plus(PG_USER)
    password = quote_plus(PG_PASSWORD)
    url = f"postgresql+psycopg2://{user}:{password}@{PG_HOST}:{PG_PORT}/{PG_DB}"
    return create_engine(url)


def load(tables: dict[str, pd.DataFrame]) -> None:
    engine = get_engine()

    with engine.begin() as conn:
        for name in LOAD_ORDER:
            df = tables[name]
            # On vide la table avant de recharger (simple, idempotent pour un projet portfolio)
            conn.exec_driver_sql(f"TRUNCATE TABLE {name} CASCADE;")
            df.to_sql(name, conn, if_exists="append", index=False)
            print(f"[load] {name} -> {len(df)} lignes chargées")

    print("[load] Chargement terminé avec succès.")


if __name__ == "__main__":
    from extract import extract
    from clean import clean
    from transform import transform

    data = extract()
    cleaned_data = clean(data)
    transformed = transform(cleaned_data)
    load(transformed)

"""
clean.py
Nettoie les DataFrames : doublons, valeurs nulles, types de dates.
"""

import pandas as pd

DATE_COLUMNS = {
    "fields": [],
    "wells": ["drill_date"],
    "equipment": ["install_date"],
    "employees": ["hire_date"],
    "production": ["date"],
    "maintenance": ["date"],
    "sales": ["date"],
}


def clean(dataframes: dict[str, pd.DataFrame]) -> dict[str, pd.DataFrame]:
    cleaned = {}

    for name, df in dataframes.items():
        df = df.copy()

        # 1. Supprimer les doublons stricts
        before = len(df)
        df = df.drop_duplicates()
        removed = before - len(df)
        if removed:
            print(f"[clean] {name}: {removed} doublons supprimés")

        # 2. Convertir les colonnes de dates
        for col in DATE_COLUMNS.get(name, []):
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], errors="coerce")

        # 3. Gérer les valeurs nulles simples
        numeric_cols = df.select_dtypes(include="number").columns
        n_nulls = df[numeric_cols].isna().sum().sum()
        if n_nulls:
            print(f"[clean] {name}: {n_nulls} valeurs numériques nulles -> remplacées par 0")
            df[numeric_cols] = df[numeric_cols].fillna(0)

        # 4. Supprimer les lignes sans identifiant (clé primaire manquante)
        id_col = [c for c in df.columns if c.endswith("_id")][0] if any(
            c.endswith("_id") for c in df.columns
        ) else None
        if id_col:
            before = len(df)
            df = df.dropna(subset=[id_col])
            removed = before - len(df)
            if removed:
                print(f"[clean] {name}: {removed} lignes supprimées (id manquant)")

        cleaned[name] = df

    return cleaned


if __name__ == "__main__":
    from extract import extract

    data = extract()
    cleaned_data = clean(data)
    for name, df in cleaned_data.items():
        print(name, df.shape)

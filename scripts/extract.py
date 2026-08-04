"""
extract.py
Lit tous les fichiers CSV bruts et les renvoie sous forme de DataFrames pandas.
"""

import pandas as pd
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"

FILES = [
    "fields",
    "wells",
    "equipment",
    "employees",
    "production",
    "maintenance",
    "sales",
]


def extract() -> dict[str, pd.DataFrame]:
    """Charge tous les CSV du dossier data/ dans un dictionnaire de DataFrames."""
    dataframes = {}
    for name in FILES:
        path = DATA_DIR / f"{name}.csv"
        if not path.exists():
            raise FileNotFoundError(f"Fichier introuvable : {path}")
        df = pd.read_csv(path)
        dataframes[name] = df
        print(f"[extract] {name}.csv chargé -> {len(df)} lignes")
    return dataframes


if __name__ == "__main__":
    data = extract()
    for name, df in data.items():
        print(name, df.shape)

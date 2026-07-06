import os
import sys
import glob
import json
import pandas as pd

BRONZE_DIR = "bronze"
SILVER_DIR = "silver"

def get_latest_bronze_file() -> str:
    """Find the most recently created bronze JSON file."""
    pattern = os.path.join(BRONZE_DIR, "countries_*.json")
    files = glob.glob(pattern)

    if not files:
        sys.exit(
            f"ERROR: No bronze files found matching {pattern}."
            f"Run fetch.py first."
        )

    latest = max(files, key=os.path.getctime)
    return latest

def load_bronze(filepath: str) -> list:
    """Load the raw country list from bronze JSON file."""
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)

def flatten_countries(countries: list) -> pd.DataFrame:
    """Flatten nested JSON into a wide dataframe, one row per country."""
    df = pd.json_normalize(countries)
    print(f"Flattened {len(df)} countries with {len(df.columns)} columns.")
    print("\nColumns found: ")
    for col in sorted(df.columns):
        print(f" - {col}")
    return df

def inspect_column_types(df: pd.DataFrame) -> None:
    """Print dtype and a sample value for every column, to catch surprises."""
    print("\nColumn types and sample values: ")
    for col in df.columns:
        sample = df[col].dropna().iloc[0] if df[col].notna().any() else None
        print(f"{col:35s} dtype={str(df[col].dtype):10s} sample={sample!r}")

def build_core_table(df: pd.DataFrame) -> pd.DataFrame:
    """
    Build the core one-row-per-country table.
    Keeps a country identifier plus any columns that look like simple
    scalar quiz-relevant fields (name, capital, continent, population, etc).
    List/dict columns (languages, currencies) are excluded here and
    handled separately in build_exploded_tables().
    """

    # Extract capitals from nested list
    if "capitals" in df.columns:
        def extract_capital_name(capital_list):
            if isinstance(capital_list, list) and len(capital_list) > 0:
                first_item = capital_list[0]
                if isinstance(first_item, dict):
                    return first_item.get("name")
            return None  # Return None if the data is missing or malformed
        
        df["capitals"] = df["capitals"].apply(extract_capital_name)

    # Columns that are lists or dicts can't live in a flat table as-is
    scalar_cols = [
        col for col in df.columns
        if not df[col].apply(lambda v: isinstance(v, (list, dict))).any()
    ]
    core = df[scalar_cols].copy()

    # Clean up common dotted column names into snake_case if present
    rename_map = {}
    for col in core.columns:
        new_name = col.replace(".", "_").lower()
        rename_map[col] = new_name
    core = core.rename(columns=rename_map)

    # Type fixes only applied if the column exists, since exact field names should be confirmed against the printed column list above
    if "population" in core.columns:
        core["population"] = pd.to_numeric(core["population"], errors="coerce").astype("Int64")

    if "area" in core.columns:
        core["area"] = pd.to_numeric(core["area"], errors="coerce")

    # Drop fully empty columns — no point carrying them forward
    before = len(core.columns)
    core = core.dropna(axis=1, how="all")
    after = len(core.columns)
    if before != after:
        print(f"\nDropped {before - after} fully-empty column(s).")

    return core

def explode_dict_column(df: pd.DataFrame, id_col: str, col_name: str,
                         value_label: str) -> pd.DataFrame:
    """
    Turn a column of dicts (e.g. {'eng': 'English', 'fra': 'French'})
    into a long-format table: one row per country-value pair.
    """
    records = []
    for idx, row in df.iterrows():
        country_id = row[id_col]
        value = row.get(col_name)
        if isinstance(value, dict):
            for code, name in value.items():
                records.append({id_col: country_id, "code": code, value_label: name})
        elif isinstance(value, list):
            for item in value:
                records.append({id_col: country_id, value_label: item})

    return pd.DataFrame(records)

def build_exploded_tables(df: pd.DataFrame) -> dict:
    """
    Build long-format tables for multi-value fields like languages
    and currencies, if those columns exist in the flattened data.
    """
    # Find a stable identifier column to join back on
    id_candidates = [c for c in df.columns if "alpha_2" in c.lower() or c.lower() == "cca2"]
    id_col = id_candidates[0] if id_candidates else df.columns[0]

    exploded = {}
    for col in df.columns:
        col_lower = col.lower()
        is_container = df[col].apply(lambda v: isinstance(v, (list, dict))).any()
        if not is_container:
            continue
        if "language" in col_lower:
            table = explode_dict_column(df, id_col, col, "language")
            if not table.empty:
                exploded["languages"] = table
        elif "currenc" in col_lower:
            table = explode_dict_column(df, id_col, col, "currency")
            if not table.empty:
                exploded["currencies"] = table
    return exploded

def save_silver(core: pd.DataFrame, exploded: dict) -> None:
    """Save the core table and any exploded tables to silver/."""
    os.makedirs(SILVER_DIR, exist_ok=True)

    core_path = os.path.join(SILVER_DIR, "countries.parquet")
    core.to_parquet(core_path, index=False)
    print(f"\nSaved core table: {core_path} ({len(core)} rows, {len(core.columns)} cols)")

    for name, table in exploded.items():
        path = os.path.join(SILVER_DIR, f"{name}.parquet")
        table.to_parquet(path, index=False)
        print(f"Saved exploded table: {path} ({len(table)} rows)")

def main():
    latest_file = get_latest_bronze_file()
    print(f"Loading bronze file: {latest_file}\n")

    countries = load_bronze(latest_file)
    df = flatten_countries(countries)
    inspect_column_types(df)

    core = build_core_table(df)
    exploded = build_exploded_tables(df)

    save_silver(core, exploded)
    print("\nDone.")

if __name__ == "__main__":
    main()
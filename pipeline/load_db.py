import os
import sys
import argparse

import pandas as pd
from sqlalchemy import create_engine
from dotenv import load_dotenv

GOLD_DIR = "gold"
SQLITE_PATH = "quiz.db"
TABLE_NAME = "quiz_countries"

def load_gold_table() -> pd.DataFrame:
    """Load the gold quiz table, preferring parquet, falling back to CSV."""
    parquet_path = os.path.join(GOLD_DIR, "quiz_countries.parquet")
    csv_path = os.path.join(GOLD_DIR, "quiz_countries.csv")

    if os.path.exists(parquet_path):
        return pd.read_parquet(parquet_path)
    elif os.path.exists(csv_path):
        return pd.read_csv(csv_path)
    else:
        sys.exit(
            f"ERROR: No table found at {parquet_path} or {csv_path}."
            f"Run gold.py first."
        )

def load_to_sqlite(df: pd.DataFrame) -> None:
    """Write the dataframe to a local SQLite file"""
    engine = create_engine(f"sqlite:///{SQLITE_PATH}")
    df.to_sql(TABLE_NAME, engine, if_exists="replace", index=False)
    print(f"Loaded {len(df)} rows into {SQLITE_PATH} (table: {TABLE_NAME})")

def load_to_supabase(df: pd.DataFrame) -> None:
    """Write the dataframe to Supabase"""
    load_dotenv()
    db_url = os.getenv("SUPABASE_DB_URL")

    if not db_url:
        sys.exit(
            "ERROR: SUPABASE_DB_URL not found in environment."
        )

    engine = create_engine(db_url)

    try:
        df.to_sql(TABLE_NAME, engine, if_exists="replace", index=False)
    except Exception as e:
        sys.exit(f"ERROR: Failed to write to Supabase.\n{e}")

    print(f"Loaded {len(df)} rows into Supabase (table: {TABLE_NAME})")

def main():
    parser = argparse.ArgumentParser(description="Load gold data into db")
    parser.add_argument(
        "--target",
        choices=["sqlite", "supabase"],
        default="sqlite",
        help="Where to load the data (default: sqlite)",
    )
    args = parser.parse_args()

    df = load_gold_table()
    print(f"Loaded table: {len(df)} rows, {len(df.columns)} columns")

    # population_distractors may be a list column — stringify it since
    # SQL databases don't have a native list type
    if "population_distractors" in df.columns:
        df["population_distractors"] = df["population_distractors"].apply(
            lambda v: ",".join(v) if isinstance(v, list) else v
        )

    if args.target == "sqlite":
        load_to_sqlite(df)
    else:
        load_to_supabase(df)

    print("Done")

if __name__ == "__main__":
    main()
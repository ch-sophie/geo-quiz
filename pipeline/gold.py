import os
import sys
import pandas as pd

SILVER_DIR = "silver"
GOLD_DIR = "gold"

# How many close-population "neighbors" to precompute per country
N_POPULATION_DISTRACTORS = 5

def load_silver_countries() -> pd.DataFrame:
    """Load the core silver country table (parquet or csv, whichever exists)."""
    parquet_path = os.path.join(SILVER_DIR, "countries.parquet")
    csv_path = os.path.join(SILVER_DIR, "countries.csv")

    if os.path.exists(parquet_path):
        return pd.read_parquet(parquet_path)
    elif os.path.exists(csv_path):
        return pd.read_csv(csv_path)
    else:
        sys.exit(
            f"ERROR: No silver country table found at {parquet_path} or {csv_path}."
            f"Run clean.py first."
        )

def find_column(df: pd.DataFrame, keyword: str) -> str:
    """Find the first column whose name contains the given keyword (case-insensitive)"""
    matches = [c for c in df.columns if keyword.lower() in c.lower()]
    return matches[0] if matches else None

def add_difficulty_tier(df: pd.DataFrame, population_col: str) -> pd.DataFrame:
    """
    Bucket countries into easy/medium/hard difficulty tiers based on
    population. Larger, better-known countries are assumed easier.
    """
    df = df.copy()

    if population_col not in df.columns:
        print(f"WARNING: population column '{population_col}' not found,"
              f"skipping difficulty tiers.")
        df["difficulty"] = "medium"
        return df

    valid_pop = df[population_col].dropna()
    if valid_pop.empty:
        print("WARNING: no valid population values, skipping difficulty tiers.")
        df["difficulty"] = "medium"
        return df

    #Split into 3 roughly-equal tiers by population rank
    q_high, q_low = valid_pop.quantile([0.66, 0.33])

    def tier(pop):
        if pd.isna(pop):
            return "medium"
        if pop >= q_high:
            return "easy"
        elif pop >= q_low:
            return "medium"
        else:
            return "hard"

    df["difficulty"] = df[population_col].apply(tier)

    print("\nDifficulty tier counts:")
    print(df["difficulty"].value_counts())
    return df

def build_population_distractors(df: pd.DataFrame, name_col: str,
                                   population_col: str) -> pd.DataFrame:
    """
    For each country, precompute a list of other countries with the
    closest population values — these become plausible wrong answers
    for population-comparison questions.
    """
    df = df.copy()

    if population_col not in df.columns or name_col not in df.columns:
        print("WARNING: missing name or population column,"
              "skipping population distractor pools.")
        df["population_distractors"] = None
        return df

    valid = df.dropna(subset=[population_col]).reset_index(drop=True)
    distractor_map = {}

    for i, row in valid.iterrows():
        this_pop = row[population_col]
        this_name = row[name_col]

        # Distance of every other country's population from this one
        others = valid[valid[name_col] != this_name].copy()
        others["pop_diff"] = (others[population_col] - this_pop).abs()
        closest = others.nsmallest(N_POPULATION_DISTRACTORS, "pop_diff")

        distractor_map[this_name] = closest[name_col].tolist()

    df["population_distractors"] = df[name_col].map(distractor_map)
    return df

def build_quiz_table(df: pd.DataFrame) -> pd.DataFrame:
    """
    Assemble the final gold quiz table: relevant columns plus the
    difficulty tier and distractor pool computed above.
    """
    name_col = find_column(df, "common") or find_column(df, "name")
    capital_col = find_column(df, "capital")
    region_col = find_column(df, "region")
    population_col = find_column(df, "population")
    flag_col = find_column(df, "emoji")

    print(f"\nDetected columns -> name: {name_col}, capital: {capital_col}, "
          f"region: {region_col}, population: {population_col}, flag: {flag_col}")

    if name_col is None:
        sys.exit("ERROR: Could not find a name column in the silver table. "
                  "Check silver/countries column names and adjust find_column keywords.")

    df = add_difficulty_tier(df, population_col)
    df = build_population_distractors(df, name_col, population_col)

    keep_cols = [c for c in [name_col, capital_col, region_col, population_col,
                              flag_col, "difficulty", "population_distractors"]
                 if c is not None]

    quiz_table = df[keep_cols].copy()

    rename_map = {}
    if name_col:
        rename_map[name_col] = "name"
    if capital_col:
        rename_map[capital_col] = "capital"
    if region_col:
        rename_map[region_col] = "region"
    if population_col:
        rename_map[population_col] = "population"
    if flag_col:
        rename_map[flag_col] = "flag"
    quiz_table = quiz_table.rename(columns=rename_map)

    return quiz_table

def save_gold(quiz_table: pd.DataFrame) -> None:
    """Save the gold quiz table as both parquet and CSV for flexibility."""
    os.makedirs(GOLD_DIR, exist_ok=True)

    csv_path = os.path.join(GOLD_DIR, "quiz_countries.csv")
    quiz_table.to_csv(csv_path, index=False)
    print(f"\nSaved gold table: {csv_path} ({len(quiz_table)} rows)")

    try:
        parquet_path = os.path.join(GOLD_DIR, "quiz_countries.parquet")
        quiz_table.to_parquet(parquet_path, index=False)
        print(f"Saved gold table: {parquet_path}")
    except ImportError:
        print("(Skipped parquet output")

def main():
    df = load_silver_countries()
    print(f"Loaded silver table: {len(df)} rows, {len(df.columns)} columns")

    quiz_table = build_quiz_table(df)
    save_gold(quiz_table)

    print("\nDone.")

if __name__ == "__main__":
    main()
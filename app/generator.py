import ast
import random
import pandas as pd

def _parse_distractor_list(value):
    """
    Normalize the population_distractors field back into a real list.
    Depending on how the data was saved, this might arrive as:
      - an actual Python list (loaded from parquet)
      - a string that looks like a list, e.g. "['France', 'Spain']" (from CSV)
      - a plain comma-joined string, e.g. "France,Spain" (from load.py's SQL prep)
    """
    if isinstance(value, list):
        return value
    if not isinstance(value, str) or not value.strip():
        return []
    # Try parsing as a real Python list literal first
    try:
        parsed = ast.literal_eval(value)
        if isinstance(parsed, list):
            return parsed
    except (ValueError, SyntaxError):
        pass

    # Fall back to a plain comma-split
    return [v.strip() for v in value.split(",") if v.strip()]

def _sample_wrong_names(df: pd.DataFrame, name_col: str, correct_name: str,
                         n: int = 3) -> list:
    """Pick n random country names, excluding the correct answer."""
    pool = df[df[name_col] != correct_name][name_col].dropna().tolist()
    return random.sample(pool, min(n, len(pool)))

def _build_options(correct: str, wrong_options: list) -> list:
    """Combine correct answer with distractors and shuffle."""
    options = wrong_options + [correct]
    random.shuffle(options)
    return options

def get_capital_question(df: pd.DataFrame, name_col: str = "name",
                          capital_col: str = "capital") -> dict:
    """'What is the capital of X?' — wrong answers are random other capitals."""
    valid = df.dropna(subset=[name_col, capital_col])
    if valid.empty:
        raise ValueError(f"No rows with both '{name_col}' and '{capital_col}' populated.")

    row = valid.sample(1).iloc[0]
    country = row[name_col]
    correct_capital = row[capital_col]

    wrong_capitals = _sample_wrong_names(valid, capital_col, correct_capital, n=3)
    options = _build_options(correct_capital, wrong_capitals)

    return {
        "type": "capital",
        "question": f"What is the capital of {country}?",
        "options": options,
        "answer": correct_capital,
        "image_url": None,
        "country": country,
    }

def get_country_from_capital_question(df: pd.DataFrame, name_col: str = "name",
                                        capital_col: str = "capital") -> dict:
    """'Which country has the capital?'"""
    valid = df.dropna(subset=[name_col, capital_col])
    if valid.empty:
        raise ValueError(f"No rows with both '{name_col}' and '{capital_col}' populated.")

    row = valid.sample(1).iloc[0]
    country = row[name_col]
    capital = row[capital_col]

    wrong_countries = _sample_wrong_names(valid, name_col, country, n=3)
    options = _build_options(country, wrong_countries)

    return {
        "type": "country_from_capital",
        "question": f"{capital} is the capital of?",
        "options": options,
        "answer": country,
        "image_url": None,
        "country": country,
    }

def get_flag_question(df: pd.DataFrame, name_col: str = "name",
                       flag_col: str = "flag") -> dict:
    valid = df.dropna(subset=[name_col, flag_col])
    if valid.empty:
        raise ValueError(f"No rows with both '{name_col}' and '{flag_col}' populated.")

    row = valid.sample(1).iloc[0]
    country = row[name_col]
    flag_emoji = row[flag_col]

    wrong_countries = _sample_wrong_names(valid, name_col, country, n=3)
    options = _build_options(country, wrong_countries)

    return {
        "type": "flag",
        "question": "Which country does this flag belong to?",
        "options": options,
        "answer": country,
        "image_url": None,
        "emoji": flag_emoji,
        "country": country,
    }

def get_region_question(df: pd.DataFrame, name_col: str = "name",
                         region_col: str = "region") -> dict:
    """'Which continent is X in?'"""
    valid = df.dropna(subset=[name_col, region_col])
    if valid.empty:
        raise ValueError(f"No rows with both '{name_col}' and '{region_col}' populated.")

    row = valid.sample(1).iloc[0]
    country = row[name_col]
    correct_region = row[region_col]

    all_regions = valid[region_col].dropna().unique().tolist()
    other_regions = [r for r in all_regions if r != correct_region]
    wrong_regions = random.sample(other_regions, min(3, len(other_regions)))
    options = _build_options(correct_region, wrong_regions)

    return {
        "type": "region",
        "question": f"Which continent is {country} in?",
        "options": options,
        "answer": correct_region,
        "image_url": None,
        "country": country,
    }

def get_population_question(df: pd.DataFrame, name_col: str = "name",
                             population_col: str = "population",
                             distractor_col: str = "population_distractors") -> dict:
    """
    'Which country has a population closest to X?' — uses the
    precomputed population-neighbor distractor pool from gold.py,
    so wrong answers are similar order-of-magnitude, not random.
    """
    valid = df.dropna(subset=[name_col, population_col])
    if valid.empty:
        raise ValueError(f"No rows with both '{name_col}' and '{population_col}' populated.")

    row = valid.sample(1).iloc[0]
    country = row[name_col]
    population = row[population_col]

    distractor_pool = _parse_distractor_list(row.get(distractor_col))
    # Remove the correct answer if it somehow ended up in its own pool
    distractor_pool = [c for c in distractor_pool if c != country]

    if len(distractor_pool) < 3:
        # Fall back to random sampling if the pool is too small/missing
        wrong_countries = _sample_wrong_names(valid, name_col, country, n=3)
    else:
        wrong_countries = random.sample(distractor_pool, 3)

    options = _build_options(country, wrong_countries)

    return {
        "type": "population",
        "question": f"Which of these countries has a population closest to {int(population):,}?",
        "options": options,
        "answer": country,
        "image_url": None,
        "country": country,
    }

QUESTION_GENERATORS = {
    "capital": get_capital_question,
    "country_from_capital": get_country_from_capital_question,
    "flag": get_flag_question,
    #"region": get_region_question,
    "population": get_population_question,
}

def get_random_question(df: pd.DataFrame, question_type: str = None,
                         exclude_countries: set = None, name_col: str = "name") -> dict:
    """
    Get one random question. If question_type is given, uses that
    generator specifically; otherwise picks a random type.

    exclude_countries: a set of country names already asked about this
    round. If excluding them would leave too few rows to build a
    question (need at least 4 for distractors), the exclusion is
    dropped for this call rather than crashing — this only matters if
    a round runs long enough to exhaust the whole dataset.
    """
    if question_type is None:
        question_type = random.choice(list(QUESTION_GENERATORS.keys()))

    generator = QUESTION_GENERATORS.get(question_type)
    if generator is None:
        raise ValueError(f"Unknown question type: {question_type}")

    if exclude_countries and name_col in df.columns:
        remaining = df[~df[name_col].isin(exclude_countries)]
        if len(remaining) >= 4:
            df = remaining

    return generator(df)

if __name__ == "__main__":
    # Quick manual test — load gold data and print one of each question type
    import os

    gold_path = os.path.join("gold", "quiz_countries.csv")
    if not os.path.exists(gold_path):
        print(f"No gold file found at {gold_path}. Run gold.py first.")
    else:
        df = pd.read_csv(gold_path)
        print(f"Loaded {len(df)} rows from {gold_path}\n")

        for qtype in QUESTION_GENERATORS:
            try:
                q = get_random_question(df, question_type=qtype)
                print(f"[{q['type']}] {q['question']}")
                print(f"  options: {q['options']}")
                print(f"  answer:  {q['answer']}\n")
            except ValueError as e:
                print(f"[{qtype}] SKIPPED — {e}\n")
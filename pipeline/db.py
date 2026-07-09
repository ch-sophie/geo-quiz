import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv
from datetime import datetime
import pandas as pd

SQLITE_PATH = "quiz.db"
TABLE_NAME = "leaderboard"

def get_engine():
    """Return a SQLAlchemy engine — Supabase if configured, else local SQLite."""
    load_dotenv()
    db_url = os.getenv("SUPABASE_DB_URL")

    if db_url:
        return create_engine(db_url)
    return create_engine(f"sqlite:///{SQLITE_PATH}")

def init_leaderboard_table(engine) -> None:
    """Create the leaderboard table if it doesn't already exist."""
    with engine.begin() as conn:
        conn.execute(text(f"""
            CREATE TABLE IF NOT EXISTS {TABLE_NAME} (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                player_name TEXT NOT NULL,
                score INTEGER NOT NULL,
                total_questions INTEGER NOT NULL,
                category TEXT,
                difficulty TEXT,
                played_at TEXT NOT NULL
            )
        """))

def save_score(engine, player_name: str, score: int, total_questions: int,
               category: str, difficulty: str) -> None:
    """Insert one completed quiz result into the leaderboard."""
    with engine.begin() as conn:
        conn.execute(
            text(f"""
                INSERT INTO {TABLE_NAME}
                    (player_name, score, total_questions, category, difficulty, played_at)
                VALUES
                    (:player_name, :score, :total_questions, :category, :difficulty, :played_at)
            """),
            {
                "player_name": player_name,
                "score": score,
                "total_questions": total_questions,
                "category": category,
                "difficulty": difficulty,
                "played_at": datetime.now().isoformat(timespec="seconds"),
            },
        )

def get_top_scores(engine, limit: int = 10):
    """Return the top N scores, ordered by score desc, then most recent first."""
    query = text(f"""
        SELECT player_name, score, total_questions, category, difficulty, played_at
        FROM {TABLE_NAME}
        ORDER BY score DESC, played_at DESC
        LIMIT :limit
    """)
    with engine.connect() as conn:
        return pd.read_sql(query, conn, params={"limit": limit})
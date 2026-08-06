
#### 1. Bronze layer ingestion script (fetch)
- Pulls raw country data from the REST Countries API and saves it,
untouched, to a timestamped JSON file in the bronze/ directory.

- No cleaning, flattening, or transformation happens here (that's
silver's job). This script's only responsibility is: call the API,
verify the response, and save exactly what came back.

#### 2. Silver layer transformation script (clean)
- Loads the most recent bronze JSON file, flattens the nested structure,
fixes types, and splits multi-value fields (languages, currencies) into
their own long-format tables. Saves clean, typed tables to silver/ directory.

- This script doesn't know or care what the quiz app needs (that's
gold's job). Silver just makes the data trustworthy and well-typed.

#### 3. Gold layer transformation script
- Loads silver tables and builds quiz-ready output: difficulty tiers and
precomputed distractor pools where random sampling would produce bad
questions (e.g. population, where "Vatican City vs China" is unfair).

- For question types where any wrong country is a fine distractor
(flags, capitals, regions), no precomputation is needed, the app can
sample randomly from the core table at question time.

#### 4. Load_db - Load gold data into db
- Supports two targets:
  - sqlite   : writes to a local .db file (fast local dev, no server needed)
  - supabase : writes to Supabase Postgres instance (for deployment,
               since Render's filesystem is ephemeral and can't hold a
               SQLite file across restarts)

- Usage:
    - python3 pipeline/load_db.py --target sqlite
    - python3 pipeline/load_db.py --target supabase

##### --- SET UP TO DO !!! --- 
- Supabase requires a connection string in .env file:
    - SUPABASE_DB_URL=postgresql://user:password@host:port/dbname

#### 5. generator.py — Pure question-generation functions
- These functions take the gold quiz dataframe and return a question as
a plain dict:
    ```
    {
        "type": "capital",
        "question": "What is the capital of France?",
        "options": ["Paris", "Lyon", "Berlin", "Madrid"],
        "answer": "Paris",
        "image_url": None,  #or a flag URL, for flag questions
    }
    ```

- No Streamlit, no UI, no session state — just data in, question dict
out. This makes them testable on their own and reusable if the
frontend ever changes.

#### 6. db.py — Leaderboard storage
Uses Supabase (Postgres) if SUPABASE_DB_URL is set in the environment,
otherwise falls back to a local SQLite file.

##### Features to add
`ADD regions (continent) choice`
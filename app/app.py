import os
import random
import pandas as pd
import streamlit as st
from generator import get_random_question, QUESTION_GENERATORS
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))
from pipeline.db import get_engine, init_leaderboard_table, save_score, get_top_scores

GOLD_CSV_PATH = os.path.join("gold", "quiz_countries.csv")
TOTAL_QUESTIONS = 15

### DATA LOADING AND CACHING
@st.cache_resource
def get_db_engine():
    """Create the DB engine once per session and make sure the table exists."""
    engine = get_engine()
    init_leaderboard_table(engine)
    return engine

@st.cache_data
def load_quiz_data() -> pd.DataFrame:
    """Load the gold quiz table once and cache it across reruns."""
    if not os.path.exists(GOLD_CSV_PATH):
        st.error(
            f"Could not find {GOLD_CSV_PATH}. "
            f"Run the pipeline (fetch.py -> clean.py -> gold.py) first."
        )
        st.stop()
    return pd.read_csv(GOLD_CSV_PATH)

### SESSION STATE MANAGEMENT
CATEGORIES = {
    "Mixed": None,
    "Capitals": "capital",
    "Flags": "flag",
    "Countries": "country_from_capital",
}

DIFFICULTIES = ["Any", "Easy", "Medium", "Hard"]

def init_session_state():
    """Set up quiz state on first load."""
    defaults = {
        "quiz_started": False,
        "category": None,
        "difficulty": "Any",
        "player_name": "",
        "score": 0,
        "question_number": 0,
        "current_question": None,
        "answered": False,
        "selected_option": None,
        "quiz_finished": False,
        "mistakes": [],
        "score_saved": False,
        "asked_countries": set(),
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

def go_home():
    """Return to the category selection screen."""
    st.session_state.quiz_started = False
    st.session_state.category = None
    st.session_state.quiz_finished = False

def start_new_quiz(category_label: str = None, difficulty: str = None):
    """Reset all state to begin a fresh quiz."""
    if category_label is not None:
        st.session_state.category = category_label
    if difficulty is not None:
        st.session_state.difficulty = difficulty
    st.session_state.quiz_started = True
    st.session_state.score = 0
    st.session_state.question_number = 0
    st.session_state.current_question = None
    st.session_state.answered = False
    st.session_state.selected_option = None
    st.session_state.quiz_finished = False
    st.session_state.mistakes = []
    st.session_state.score_saved = False
    st.session_state.asked_countries = set()
    load_next_question()

def load_next_question():
    """Advance to the next question, or end the quiz if we've hit the limit."""
    if st.session_state.question_number >= TOTAL_QUESTIONS:
        st.session_state.quiz_finished = True
        return

    df = load_quiz_data()

    # Filter to the selected difficulty if one was chosen and enough rows remain
    difficulty = st.session_state.difficulty
    if difficulty and difficulty != "Any" and "difficulty" in df.columns:
        filtered = df[df["difficulty"].str.lower() == difficulty.lower()]
        if len(filtered) >= 4:
            df = filtered

    question_type = CATEGORIES.get(st.session_state.category)
    question = get_random_question(
        df, question_type=question_type,
        exclude_countries=st.session_state.asked_countries,
    )
    st.session_state.current_question = question
    st.session_state.asked_countries.add(question["country"])
    st.session_state.question_number += 1
    st.session_state.answered = False
    st.session_state.selected_option = None

def submit_answer(selected: str):
    """Record the user's answer, update the score, and log mistakes."""
    st.session_state.answered = True
    st.session_state.selected_option = selected
    q = st.session_state.current_question
 
    if selected == q["answer"]:
        st.session_state.score += 1
    else:
        st.session_state.mistakes.append({
            "question": q["question"],
            "your_answer": selected,
            "correct_answer": q["answer"],
        })

### UI RENDERING
def render_home():
    """Show the category selection landing page."""
    st.title("🌍 Geo Quiz")
    st.write("Test your knowledge of world capitals, flags, and countries.")

    player_name = st.text_input(
        "Your name (for the leaderboard)", value=st.session_state.player_name,
        placeholder="Anonymous",
    )

    st.subheader("Choose a difficulty")
    difficulty = st.radio(
        "Difficulty", DIFFICULTIES, horizontal=True, label_visibility="collapsed",
    )

    st.subheader("Choose a category")
    col1, col2 = st.columns(2)
    columns = [col1, col2, col1, col2]
 
    for (label, _), col in zip(CATEGORIES.items(), columns):
        with col:
            if st.button(label, use_container_width=True, key=f"cat_{label}"):
                st.session_state.player_name = player_name.strip() or "Anonymous"
                start_new_quiz(category_label=label, difficulty=difficulty)
                st.rerun()

    st.divider()
    st.subheader("🏆 Leaderboard")
    engine = get_db_engine()
    top_scores = get_top_scores(engine, limit=10)
    if top_scores.empty:
        st.caption("No scores yet — be the first to play!")
    else:
        st.dataframe(top_scores, use_container_width=True, hide_index=True)

def render_question(q: dict):
    """Render the current question, its options, and feedback if answered."""
    st.subheader(q["question"])

    if q.get("image_url"):
        col1, col2, col3 = st.columns([1, 1, 1])
        with col2:
            st.image(q["image_url"], width=250)
    elif q.get("emoji"):
        st.markdown(
            f"<div style='text-align: center; font-size: 120px;'>{q['emoji']}</div>",
            unsafe_allow_html=True,
        )
    for option in q["options"]:
        is_selected = st.session_state.selected_option == option
        disabled = st.session_state.answered

        if st.button(option, key=f"opt_{st.session_state.question_number}_{option}",
                     disabled=disabled, use_container_width=True):
            submit_answer(option)
            st.rerun()

    if st.session_state.answered:
        correct_answer = q["answer"]
        if st.session_state.selected_option == correct_answer:
            st.success(f"Correct! The answer is **{correct_answer}**.")
        else:
            st.error(
                f"Not quite **{st.session_state.selected_option}** — "
                f"the correct answer is **{correct_answer}**."
            )

        if st.button("Next question ->", type="primary"):
            load_next_question()
            st.rerun()

def render_results():
    """Show the final score screen."""
    st.title("Quiz complete!")
    st.metric("Your score", f"{st.session_state.score} / {TOTAL_QUESTIONS}")

    percentage = st.session_state.score / TOTAL_QUESTIONS * 100
    if percentage >= 80:
        st.balloons()
        st.write("Excellent work — you know your geography!")
    elif percentage >= 50:
        st.snow()
        st.write("Solid effort — a bit more practice and you'll ace it.")
    else:
        st.snow()
        st.write("Very bad — give it another shot!")

    # Save the score exactly once per completed quiz — st.session_state.score_saved
    # guards against re-saving on every rerun caused by subsequent button clicks.
    if not st.session_state.score_saved:
        engine = get_db_engine()
        save_score(
            engine,
            player_name=st.session_state.player_name or "Anonymous",
            score=st.session_state.score,
            total_questions=TOTAL_QUESTIONS,
            category=st.session_state.category,
            difficulty=st.session_state.difficulty,
        )
        st.session_state.score_saved = True
 
    if st.session_state.mistakes:
        with st.expander(f"Review your mistakes ({len(st.session_state.mistakes)})"):
            for m in st.session_state.mistakes:
                st.markdown(f"**{m['question']}**")
                st.write(f"Your answer: {m['your_answer']} | Correct answer: {m['correct_answer']}")
                st.divider()
    else:
        st.success("Perfect round!")

    col1, col2 = st.columns(2)
    with col1:
        if st.button("Play again", type="primary", use_container_width=True):
            start_new_quiz()
            st.rerun()
    with col2:
        if st.button("Home", use_container_width=True):
            go_home()
            st.rerun()
            
### MAIN 
def main():
    st.set_page_config(page_title="Geo Quiz", page_icon="🌍", layout="centered")
    init_session_state()

    if not st.session_state.quiz_started:
        render_home()
        return

    st.title("🌍 Geo Quiz")
    st.caption(f"Category: {st.session_state.category} | Difficulty: {st.session_state.difficulty}")

    # First-ever load: kick off the quiz automatically
    if st.session_state.current_question is None and not st.session_state.quiz_finished:
        load_next_question()

    if st.session_state.quiz_finished:
        render_results()
        return

    # Progress + score header
    progress = st.session_state.question_number / TOTAL_QUESTIONS
    st.progress(progress)
    st.caption(
        f"Question {st.session_state.question_number} of {TOTAL_QUESTIONS} "
        f"| Score: {st.session_state.score}"
    )

    render_question(st.session_state.current_question)

    st.divider()
    if st.button("Restart quiz"):
        start_new_quiz()
        st.rerun()

if __name__ == "__main__":
    main()
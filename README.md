# Geography quizgame 
An interactive geography trivia game built with Python and Streamlit.

**Link to the game**: [Geo Quiz](https://geo-quiz-ma9x.onrender.com)

### Architecture Overview
The project is structured around data engineering best practices using a three-tier Medallion pattern:
1. **🥉 Bronze Layer:** Caches the raw, unaltered JSON responses directly from the RestCountries API to ensure data reproducibility.
2. **🥈 Silver Layer:** Flattens complex, nested JSON arrays into clean structured data tables, processes proper data types, handles null inputs, and parses out the target fields (like country names, capital cities, and flag URLs).
3. **🥇 Gold Layer / Runtime:** Exposes highly optimized data pools to the quiz functions, ensuring that distractors (wrong answers) are cleanly filtered out and dynamically generated without breaking runtime state.

### Features
- **Capital Quiz Mode:** Guess the capital of a randomly selected country
- **Country Quiz Mode:** Guess the country when given a random capital
- **Flag Quiz Mode:** Match the correct country name to its official flag image
- **Smart Distractors:** Dynamic generation of multiple-choice options ensuring unique, non-overlapping answers every round
- **Decoupled Logic:** Game engine logic is purely function-based, separating data operations completely from the Streamlit UI presentation layer

### Tech Stack
- API: RESTCountries API
- Frontend & UI: Streamlit
- Data Engineering: Pandas, JSON, Glob
- Environment Management: Python-dotenv
- Deployment: Render

Installation: pip install -r requirements.txt
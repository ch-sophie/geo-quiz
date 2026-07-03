import os
import sys
import json
from datetime import datetime

import requests
from dotenv import load_dotenv

BASE_URL = "https://api.restcountries.com/countries/v5"
BRONZE_DIR = "bronze"
PAGE_LIMIT = 100

def get_api_key() -> str:
    """Load the API key from environment and fail loudly if missing"""
    load_dotenv()
    api_key = os.getenv("API_KEY")
    if not api_key:
        sys.exit(
            "ERROR: API_KEY not found in environment."
        )
    return api_key

def fetch_all_countries(api_key: str) -> list:
    """Fetch every country from the API, paging through results"""
    headers = {"Authorization": f"Bearer {api_key}"}
    all_countries = []
    offset = 0

    while True:
        params = {"limit": PAGE_LIMIT, "offset": offset}
        response = requests.get(BASE_URL, headers=headers, params=params)

        if response.status_code != 200:
            sys.exit(
                f"ERROR: API request failed with status {response.status_code}\n"
                f"Response body: {response.text}"
            )

        payload = response.json()["data"]
        batch = payload["objects"]
        all_countries.extend(batch)

        print(f"Fetched {len(batch)} countries (offset={offset}), "
              f"total so far: {len(all_countries)}")

        if not payload["meta"]["more"]:
            break

        offset += PAGE_LIMIT

    return all_countries

def save_raw(countries: list) -> str:
    """Save the raw country list to a timestamped file in bronze/"""
    os.makedirs(BRONZE_DIR, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filepath = os.path.join(BRONZE_DIR, f"countries_{timestamp}.json")

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(countries, f, ensure_ascii=False, indent=2)

    return filepath

def main():
    api_key = get_api_key()
    countries = fetch_all_countries(api_key)
    filepath = save_raw(countries)

    print(f"\nDone. Saved {len(countries)} countries to {filepath}")

if __name__ == "__main__":
    main()
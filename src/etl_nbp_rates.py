#!/usr/bin/env python
# coding: utf-8

# In[ ]:


#!/usr/bin/env python
# coding: utf-8

import os
import requests
import pandas as pd
from datetime import datetime, timedelta, date
from pathlib import Path

# --- CONFIGURATION ---
MAX_DAYS = 93          # NBP API limit for a single query
OUTPUT_DIR = Path.cwd() / "data"
PARQUET_FILE = "nbp_rates.parquet"
CURRENCIES = ["EUR", "USD", "GBP"]

def split_date_range(start_date: date, end_date: date, chunk_days: int = MAX_DAYS):
    """Splits a date range into chunks of max chunk_days."""
    chunks = []
    start = start_date
    while start <= end_date:
        chunk_end = start + timedelta(days=chunk_days - 1)
        if chunk_end > end_date:
            chunk_end = end_date
        chunks.append((start, chunk_end))
        start = chunk_end + timedelta(days=1)
    return chunks


def fetch_rates(currency_code: str, start_date: date, end_date: date) -> list[dict]:
    """Fetches currency rates from NBP API for a given date range."""
    url = (
        f"https://api.nbp.pl/api/exchangerates/rates/"
        f"A/{currency_code}/{start_date:%Y-%m-%d}/{end_date:%Y-%m-%d}/?format=json"
    )
    resp = requests.get(url, timeout=10)
    resp.raise_for_status()
    data = resp.json()
    return data["rates"]  # Returns list of dicts: effectiveDate, mid


def main():
    # Ensure output directory exists
    if not OUTPUT_DIR.exists():
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    full_path = OUTPUT_DIR / PARQUET_FILE

    # 1. Load existing data (if any) and determine start date for new data
    if full_path.exists():
        df_existing = pd.read_parquet(full_path)
        df_existing["rate_date"] = pd.to_datetime(df_existing["rate_date"]).dt.date
        last_date_overall = df_existing["rate_date"].max()
        print(f"Current data up to: {last_date_overall}")
        start_date_inc = last_date_overall + timedelta(days=1)
    else:
        df_existing = pd.DataFrame(
            columns=["currency_code", "rate_date", "rate"]
        )
        # If no data exists, set start date manually
        start_date_inc = date(2024, 1, 1)

    # 2. Set end date (e.g., yesterday)
    end_date_inc = date.today() - timedelta(days=1)

    if start_date_inc > end_date_inc:
        print("No new dates to download - data is up to date.")
        return

    print(f"Downloading new data from {start_date_inc} to {end_date_inc}")

    new_rows = []

    # 3. Fetch data for each currency in 93-day chunks
    for code in CURRENCIES:
        print(f"\n=== {code} ===")
        for chunk_start, chunk_end in split_date_range(start_date_inc, end_date_inc):
            print(f"Batch: {chunk_start} - {chunk_end}")
            try:
                rates = fetch_rates(code, chunk_start, chunk_end)
                for r in rates:
                    new_rows.append(
                        {
                            "currency_code": code,
                            "rate_date": datetime.strptime(
                                r["effectiveDate"], "%Y-%m-%d"
                            ).date(),
                            "rate": r["mid"],
                        }
                    )
            except Exception as e:
                print(f"Error for {code} {chunk_start} - {chunk_end}: {e}")

    if not new_rows:
        print("API returned no new data.")
        return

    # 4. Merge old + new and save as Parquet (overwrite file)
    df_new = pd.DataFrame(new_rows)
    df_all = pd.concat([df_existing, df_new], ignore_index=True)

    # Deduplicate protection (in case script is run multiple times)
    df_all = df_all.drop_duplicates(subset=["currency_code", "rate_date"])

    df_all.to_parquet(full_path, index=False)

    print(f"Saved/Updated {full_path}. Total rows: {len(df_all)}")


if __name__ == "__main__":
    main()


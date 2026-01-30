#!/usr/bin/env python
# coding: utf-8

# In[ ]:


#!/usr/bin/env python
# coding: utf-8

import openmeteo_requests
import requests_cache
import pandas as pd
from retry_requests import retry
from pathlib import Path
import datetime

# --- CONFIGURATION ---
OUTPUT_DIR = Path.cwd() / "data"
FILE_NAME = "weather_data.parquet"

# Setup Open-Meteo with cache and retry logic
cache_session = requests_cache.CachedSession('.cache', expire_after=3600)
retry_session = retry(cache_session, retries=5, backoff_factor=0.2)
openmeteo = openmeteo_requests.Client(session=retry_session)

def main():
    print("--- START: WEATHER DATA DOWNLOAD ---")

    locations = {
        "Frankfurt": {"lat": 50.11, "lon": 8.68},
        "Chicago":   {"lat": 41.85, "lon": -87.65},
        "Warszawa":  {"lat": 52.23, "lon": 21.01}
    }

    # Always fetch from the beginning of the year until today
    start_date = "2024-01-01"
    end_date = datetime.date.today().strftime("%Y-%m-%d")

    all_data = []

    for city, coords in locations.items():
        try:
            params = {
                "latitude": coords["lat"],
                "longitude": coords["lon"],
                "start_date": start_date,
                "end_date": end_date,
                "daily": ["temperature_2m_mean"], 
                "timezone": "UTC"
            }

            responses = openmeteo.weather_api("https://archive-api.open-meteo.com/v1/archive", params=params)
            response = responses[0]

            daily = response.Daily()
            dates = pd.date_range(
                start=pd.to_datetime(daily.Time(), unit="s", utc=True),
                end=pd.to_datetime(daily.TimeEnd(), unit="s", utc=True),
                freq=pd.Timedelta(seconds=daily.Interval()),
                inclusive="left"
            )

            df = pd.DataFrame({"Date": dates})
            df["City"] = city
            df["Temp_Mean_C"] = daily.Variables(0).ValuesAsNumpy()

            # Calculate HDD (Heating Degree Days)
            # Logic: If temp < 15.5C, heating is needed.
            df["HDD"] = df["Temp_Mean_C"].apply(lambda x: max(0, 15.5 - x))
            df["Date"] = df["Date"].dt.tz_localize(None)

            all_data.append(df)
            print(f"Downloaded data for: {city}")

        except Exception as e:
            print(f"Error for city {city}: {e}")

    if all_data:
        final_df = pd.concat(all_data, ignore_index=True)

        # Create directory if it doesn't exist
        if not OUTPUT_DIR.exists():
            OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

        save_path = OUTPUT_DIR / FILE_NAME

        try:
            final_df.to_parquet(save_path, index=False)
            print(f"SUCCESS: Saved to {save_path}")
        except PermissionError:
            print("ERROR: File is open in another program (e.g., Power BI). Close it and try again.")
    else:
        print("No data to save.")

if __name__ == "__main__":
    main()


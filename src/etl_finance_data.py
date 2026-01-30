#!/usr/bin/env python
# coding: utf-8

# In[ ]:


#!/usr/bin/env python
# coding: utf-8

import yfinance as yf
import pandas as pd
from pathlib import Path

# --- CONFIGURATION ---
# Define output directory relative to the script execution location
OUTPUT_DIR = Path.cwd() / "data"
FILE_NAME = "financial_data_long.parquet"

def main():
    print("--- START: FINANCIAL DATA DOWNLOAD (LONG FORMAT) ---")

    tickers = {
        "EURPLN=X": "EUR_PLN",
        "USDPLN=X": "USD_PLN",
        "CHFPLN=X": "CHF_PLN",
        "BZ=F": "Oil_Brent",
        "CL=F": "Oil_WTI",
        "NG=F": "Natural_Gas",
        "GC=F": "Gold",
        "HG=F": "Copper"
    }

    try:
        # 1. Download data
        print("Downloading data from Yahoo Finance...")
        df_raw = yf.download(list(tickers.keys()), start="2024-01-01", progress=False)

        # 2. Select Close prices
        if isinstance(df_raw.columns, pd.MultiIndex):
            df = df_raw['Close'].copy()
        else:
            df = df_raw.copy()

        # 3. Prepare for Long format transformation
        df = df.reset_index()
        df = df.rename(columns=tickers) # Rename columns to readable format

        # 4. UNPIVOT (MELT)
        # 'Date' remains strictly as an identifier, other columns become rows
        df_long = df.melt(
            id_vars=['Date'], 
            var_name='Instrument', 
            value_name='Price'
        )

        # 5. Data Cleaning
        # Remove timezones from date
        df_long['Date'] = pd.to_datetime(df_long['Date']).dt.tz_localize(None)

        # Remove rows with NaN prices (market holidays for specific exchanges)
        df_long = df_long.dropna(subset=['Price'])

        # 6. Save to file
        if not OUTPUT_DIR.exists():
            OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

        save_path = OUTPUT_DIR / FILE_NAME
        df_long.to_parquet(save_path, index=False)

        print(f"SUCCESS: Saved {len(df_long)} records to {save_path}")
        print(df_long.head()) # Data preview

    except PermissionError:
         print("ERROR: File is locked (e.g., open in Power BI/OneDrive).")
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    main()


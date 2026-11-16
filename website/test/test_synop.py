import sys
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_DIR))

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import pandas as pd

from synop_utils import scrape_synop_range


# ==================================================
# 1. TENTUKAN WAKTU PENGUJIAN
# ==================================================

selected_time = datetime(
    2025, 1, 1, 7, 0,
    tzinfo=ZoneInfo("Asia/Jakarta")
)

end_utc = selected_time.astimezone(
    ZoneInfo("UTC")
)

start_utc = end_utc - timedelta(hours=5)


print("Waktu pilihan WIB :", selected_time)
print("Waktu awal UTC    :", start_utc)
print("Waktu akhir UTC   :", end_utc)


# ==================================================
# 2. SCRAPING
# ==================================================

df = scrape_synop_range(
    start_datetime=start_utc,
    end_datetime=end_utc
)


# ==================================================
# 3. PERIKSA HASIL
# ==================================================

if df.empty:

    print("\nTidak ada data yang berhasil diperoleh.")

else:

    print("\nData hasil scraping:")
    print(df.to_string(index=False))

    print("\nInformasi DataFrame:")
    df.info()

    print("\nPemeriksaan timestamp:")
    print(df["data_timestamp"])

    print("\nPemeriksaan duplikasi:")
    print(
        "Jumlah duplikat:",
        df["data_timestamp"].duplicated().sum()
    )

    print("\nSebaran fenomena WW:")
    print(df["phenomenon"].value_counts(dropna=False))

    print("\nJumlah data:")
    print(len(df))

    print("\nKolom:")
    print(df.columns.tolist())
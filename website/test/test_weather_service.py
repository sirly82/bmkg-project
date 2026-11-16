import sys
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_DIR))

import pandas as pd
from weather_service import get_six_hour_data

selected_wib = pd.Timestamp(
    "2025-01-01 07:00:00",
    tz="Asia/Jakarta"
)


# ============================================================
# PENGUJIAN PERTAMA
# ============================================================

print("=" * 60)
print("PENGUJIAN PERTAMA")
print("=" * 60)

df_first = get_six_hour_data(selected_wib)

print("\nHasil pengujian pertama:")
print(
    df_first[
        ["data_timestamp", "phenomenon", "weather_code_ww"]
    ].to_string(index=False)
)


# ============================================================
# PENGUJIAN KEDUA
# ============================================================

print("\n" + "=" * 60)
print("PENGUJIAN KEDUA")
print("=" * 60)

df_second = get_six_hour_data(selected_wib)

print("\nHasil pengujian kedua:")
print(
    df_second[
        ["data_timestamp", "phenomenon", "weather_code_ww"]
    ].to_string(index=False)
)


# ============================================================
# PEMERIKSAAN
# ============================================================

assert len(df_first) == len(df_second)

assert df_first["data_timestamp"].equals(
    df_second["data_timestamp"]
)

print("\nPengujian cache berhasil.")
import sys
import time
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_DIR))

import pandas as pd
from modules.weather_service import get_hours_data

selected_wib = pd.Timestamp(
    "2025-01-01 07:00:00",
    tz="Asia/Jakarta"
)

# ============================================================
# PENGUJIAN PERTAMA (SCRAPE + SIMPAN CACHE)
# ============================================================
print("=" * 60)
print("PENGUJIAN PERTAMA")
print("=" * 60)

t0 = time.perf_counter()
df_first = get_hours_data(selected_wib)
durasi_1 = time.perf_counter() - t0

print(f"\nWaktu eksekusi pertama: {durasi_1:.2f} detik")
print(
    df_first[
        ["data_timestamp", "timestamp_local", "phenomenon", "weather_code_ww"]
    ].to_string(index=False)
)

# ============================================================
# PENGUJIAN KEDUA (BACA FULL DARI SQLITE CACHE)
# ============================================================
print("\n" + "=" * 60)
print("PENGUJIAN KEDUA")
print("=" * 60)

t1 = time.perf_counter()
df_second = get_hours_data(selected_wib)
durasi_2 = time.perf_counter() - t1

print(f"\nWaktu eksekusi kedua: {durasi_2:.4f} detik")
print(
    df_second[
        ["data_timestamp", "timestamp_local", "phenomenon", "weather_code_ww"]
    ].to_string(index=False)
)

# ============================================================
# PEMERIKSAAN
# ============================================================
assert not df_first.empty, "Data hasil pengujian pertama kosong."
assert len(df_first) == len(df_second), "Jumlah baris cache tidak sama."
assert df_first["data_timestamp"].equals(df_second["data_timestamp"]), "Timestamp tidak identik."

print("\nPengujian cache berhasil.")
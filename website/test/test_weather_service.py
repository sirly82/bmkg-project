import sys
import time
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_DIR))

import pandas as pd
from modules.weather_service import get_hours_data, get_window_bounds

selected_wib = pd.Timestamp(
    "2025-01-01 07:00:00",
    tz="Asia/Jakarta"
)

bounds = get_window_bounds(selected_wib)
print("Batas window (UTC):", bounds)

# ============================================================
# PENGUJIAN PERTAMA (SCRAPE + SIMPAN CACHE)
# ============================================================
print("\n" + "=" * 60)
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
assert df_first["data_timestamp"].min() >= bounds["fetch_start_utc"]
assert df_first["data_timestamp"].max() <= bounds["forecast_utc"]
assert bounds["forecast_utc"] in set(df_first["data_timestamp"]), "Data t+1 belum ikut terambil!"

print("\nPengujian cache & window 28 jam (t-26 s.d. t+1) berhasil.")
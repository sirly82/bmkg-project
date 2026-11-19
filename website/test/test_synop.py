import sys
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_DIR))

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from modules.synop_utils import classify_phenomenon, scrape_synop_range

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

# ==================================================
# 4. VALIDASI SKEMA & LOGIKA KLASIFIKASI BARU
# ==================================================
if not df.empty:
    assert "temp_wetbulb_c" not in df.columns, "Kolom temp_wetbulb_c masih ada!"
    assert df["data_timestamp"].duplicated().sum() == 0, "Ditemukan timestamp duplikat!"

# Uji langsung mapping kode WW baru
assert classify_phenomenon("02") == "Normal"
assert classify_phenomenon("05") == "Haze/Smoke/Dust"
assert classify_phenomenon("10") == "Mist"
assert classify_phenomenon("45") == "Fog"
assert classify_phenomenon("61") == "Active Precipitation"
assert classify_phenomenon("25") == "Recent/Distant Precipitation"
assert classify_phenomenon("13") == "Other"
assert classify_phenomenon(None, ix_flag="2") == "Normal"

print("\nSemua pengujian SYNOP dan klasifikasi WW berhasil.")
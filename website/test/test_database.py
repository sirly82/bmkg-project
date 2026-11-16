import sys
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_DIR))

import pandas as pd

from modules.database import (
    init_db,
    save_reports,
    get_reports,
    count_reports,
    get_cached_timestamps,
)
from modules.synop_utils import scrape_synop_range

# ============================================================
# 1. WAKTU PENGUJIAN
# ============================================================

selected_wib = pd.Timestamp(
    "2025-01-01 07:00:00",
    tz="Asia/Jakarta"
)

end_utc = selected_wib.tz_convert("UTC")
start_utc = end_utc - pd.Timedelta(hours=5)


# ============================================================
# 2. INISIALISASI DATABASE
# ============================================================

init_db()

print("Database berhasil diinisialisasi.")


# ============================================================
# 3. SCRAPING DATA
# ============================================================

df = scrape_synop_range(
    start_datetime=start_utc,
    end_datetime=end_utc
)

if df.empty:
    raise RuntimeError("Tidak ada data hasil scraping.")


# ============================================================
# 4. MENYIMPAN DATA KE SQLITE
# ============================================================

saved_count = save_reports(df)

print(f"\nJumlah laporan yang diproses: {len(df)}")
print(f"Jumlah laporan yang disimpan/diperbarui: {saved_count}")
print(f"Total data dalam database: {count_reports()}")


# ============================================================
# 5. MEMBACA KEMBALI DATA
# ============================================================

df_db = get_reports(
    start_datetime=start_utc,
    end_datetime=end_utc
)

print("\nData hasil pembacaan SQLite:")
print(df_db.to_string(index=False))


# ============================================================
# 6. MEMERIKSA TIMESTAMP
# ============================================================

print("\nTimestamp yang tersimpan:")

for timestamp in get_cached_timestamps(
    start_utc,
    end_utc
):
    print(timestamp)


# ============================================================
# 7. MEMERIKSA JUMLAH DATA
# ============================================================

print("\nJumlah data hasil scraping :", len(df))
print("Jumlah data hasil SQLite   :", len(df_db))

assert len(df) == len(df_db), (
    "Jumlah data hasil SQLite tidak sesuai."
)

assert df_db["data_timestamp"].is_unique, (
    "Ditemukan timestamp duplikat dalam database."
)

print("\nPengujian database berhasil.")
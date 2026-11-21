import sys
import sqlite3
import tempfile
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_DIR))

import pandas as pd

import modules.database as database
from modules.database import (
    COLUMNS,
    count_reports,
    get_checked_hours,
    get_reports,
    init_db,
    mark_hours_checked,
    save_reports,
)
from modules.synop_utils import scrape_synop_range

# ============================================================
# 0. ARAHKAN KE DATABASE SEMENTARA (weather.db asli aman)
# ============================================================
tmp = tempfile.TemporaryDirectory()
database.DB_DIR = Path(tmp.name)
database.DB_PATH = Path(tmp.name) / "weather_test.db"


def table_columns(table="weather_observations"):
    with sqlite3.connect(database.DB_PATH) as conn:
        return {r[1] for r in conn.execute(f"PRAGMA table_info({table})")}


# ============================================================
# 1. UJI MIGRASI DARI SKEMA LAMA
# ============================================================
with sqlite3.connect(database.DB_PATH) as conn:
    conn.execute(
        "CREATE TABLE weather_observations ("
        "data_timestamp TEXT PRIMARY KEY, cloud_low_cover_1 INTEGER)"
    )
    conn.execute(database.CREATE_CACHE_SQL)
    conn.execute(
        "INSERT INTO weather_observations VALUES ('2025-01-01 00:00:00', 6)"
    )
    conn.execute(
        "INSERT INTO synop_hour_cache VALUES ('2025-01-01 00:00:00', '2025-01-02 00:00:00')"
    )

init_db()

cols = table_columns()
assert "cloud_low_cover_1" not in cols, "Kolom lama belum di-rename!"
assert "cloud_low_cover_oktas" in cols
assert "cloud_med_cover_oktas" in cols

with sqlite3.connect(database.DB_PATH) as conn:
    val = conn.execute(
        "SELECT cloud_low_cover_oktas FROM weather_observations"
    ).fetchone()[0]
    cache_rows = conn.execute("SELECT COUNT(*) FROM synop_hour_cache").fetchone()[0]

assert val == 6, "Nilai lama hilang setelah rename!"
assert cache_rows == 0, "Cache jam belum dikosongkan setelah migrasi!"
print("Migrasi skema lama: OK")

# Migrasi kedua kali tidak boleh error / mengubah apa pun
init_db()
print("Migrasi idempoten: OK")

# ============================================================
# 2. UJI SKEMA BARU (DATABASE BERSIH)
# ============================================================
database.DB_PATH = Path(tmp.name) / "weather_fresh.db"
init_db()

cols = table_columns()
missing = set(COLUMNS) - cols
assert not missing, f"COLUMNS punya kolom yang tidak ada di tabel: {missing}"
assert "cloud_low_cover_1" not in cols
print("Skema baru: OK")

# ============================================================
# 3. SCRAPING + SIMPAN + BACA ULANG
# ============================================================
selected_wib = pd.Timestamp("2025-01-01 07:00:00", tz="Asia/Jakarta")
end_utc = selected_wib.tz_convert("UTC")
start_utc = end_utc - pd.Timedelta(hours=5)

df = scrape_synop_range(start_datetime=start_utc, end_datetime=end_utc)
if df.empty:
    raise SystemExit("GAGAL: tidak ada data dari Ogimet (cek koneksi / rate limit).")

save_reports(df)
total_1 = count_reports()

df_db = get_reports(start_utc, end_utc)
print("\nData hasil pembacaan SQLite:")
print(df_db.to_string(index=False))

assert len(df) == len(df_db), "Jumlah data SQLite tidak sesuai."
assert df_db["data_timestamp"].is_unique, "Timestamp duplikat di database."

# Nilai kosong (NULL) harus terbaca sama dengan hasil scraping
for col in ["cloud_low_cover_oktas", "cloud_med_cover_oktas", "visibility_vv"]:
    assert df[col].isna().sum() == df_db[col].isna().sum(), f"NULL {col} tidak cocok"
    assert (
        df[col].dropna().astype(float).tolist()
        == df_db[col].dropna().astype(float).tolist()
    ), f"Nilai {col} berubah setelah simpan/baca"

# Simpan ulang data yang sama: tidak boleh menambah baris (upsert)
save_reports(df)
assert count_reports() == total_1, "Simpan ulang menambah baris!"
print("Simpan, baca, dan upsert: OK")

# ============================================================
# 4. UJI CACHE JAM
# ============================================================
hours = list(pd.date_range(start_utc, end_utc, freq="h").tz_localize(None))
assert len(get_checked_hours(start_utc, end_utc)) == 0

mark_hours_checked(hours[:3])
checked = get_checked_hours(start_utc, end_utc)
assert checked == set(hours[:3]), "Cache jam tidak sesuai."

mark_hours_checked(hours[:3])  # ulang, tidak boleh error / dobel
assert len(get_checked_hours(start_utc, end_utc)) == 3
print("Cache jam: OK")

tmp.cleanup()
print("\nPengujian database berhasil.")
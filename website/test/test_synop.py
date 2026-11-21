import sys
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_DIR))

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from modules.synop_utils import (
    classify_phenomenon,
    parse_synop_row,
    scrape_synop_range,
)

# ==================================================
# 1. TENTUKAN WAKTU PENGUJIAN
# ==================================================
selected_time = datetime(2025, 2, 28, 23, 0, tzinfo=ZoneInfo("Asia/Jakarta"))
end_utc = selected_time.astimezone(ZoneInfo("UTC"))
start_utc = end_utc - timedelta(days=3)

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
# 4. VALIDASI SKEMA (DATA LIVE)
# ==================================================
if df.empty:
    raise SystemExit("GAGAL: tidak ada data dari Ogimet (cek koneksi / rate limit).")

for col in ["cloud_low_cover_oktas", "cloud_med_cover_oktas", "visibility_vv"]:
    assert col in df.columns, f"Kolom {col} tidak ada!"

assert "cloud_low_cover_1" not in df.columns, "Nama kolom lama masih ada!"
assert "temp_wetbulb_c" not in df.columns, "Kolom temp_wetbulb_c masih ada!"
assert df["data_timestamp"].duplicated().sum() == 0, "Ditemukan timestamp duplikat!"

for col in ["cloud_low_cover_oktas", "cloud_med_cover_oktas"]:
    assert df[col].dropna().between(0, 8).all(), f"{col} di luar 0-8 okta!"

print("\nPersentase kosong:")
print(df[["cloud_low_cover_oktas", "cloud_med_cover_oktas",
          "visibility_vv"]].isna().mean() * 100)

# ==================================================
# 5. UJI DECODING OFFLINE (STRING SYNOP BUATAN)
# ==================================================
def make_row(nddff, cloud_group="", tail=""):
    body = " ".join(filter(None, [
        "96195", "32970", nddff, "10265", "20240",
        "30105", "40100", "70200", cloud_group, tail,
    ])) + "="
    return ["SYNOP", "01/01/2025 00:00", "AAXX 01004", body]

# (Nddff, grup 8, seksi 333, low_expected, med_expected)
cases = [
    ("31505", "82500", "",          2, 0),     # awan rendah ada, CM=0
    ("41505", "84030", "",          0, 4),     # CL=0, Nh = awan menengah
    ("31505", "82530", "333 82330", 2, 2),     # med dari lapisan seksi 333
    ("31505", "82530", "",          2, None),  # med tidak bisa ditentukan
    ("00000", "",      "",          0, 0),     # cerah, grup 8 tidak dikirim
]

for nddff, grp8, tail, low, med in cases:
    r = parse_synop_row(make_row(nddff, grp8, tail))
    assert r is not None, f"Gagal parse: {nddff} {grp8}"
    assert r["cloud_low_cover_oktas"] == low, (grp8, r["cloud_low_cover_oktas"])
    assert r["cloud_med_cover_oktas"] == med, (grp8, r["cloud_med_cover_oktas"])

# Cek field umum dari kasus pertama
r = parse_synop_row(make_row("31505", "82500"))
assert r["visibility_vv"] == 20.0
assert r["wind_dir_deg_dd"] == 150 and r["wind_speed_ff"] == 5
assert r["temp_drybulb_c_tttttt"] == 26.5
assert r["phenomenon"] == "Normal"
assert "temp_wetbulb_c" not in r

# ==================================================
# 6. UJI KLASIFIKASI WW
# ==================================================
assert classify_phenomenon("02") == "Normal"
assert classify_phenomenon("05") == "Haze/Smoke/Dust"
assert classify_phenomenon("10") == "Mist"
assert classify_phenomenon("45") == "Fog"
assert classify_phenomenon("61") == "Active Precipitation"
assert classify_phenomenon("25") == "Recent/Distant Precipitation"
assert classify_phenomenon("13") == "Other"
assert classify_phenomenon(None, ix_flag="2") == "Normal"

# Tambahan: batas dan input tidak valid
assert classify_phenomenon("00") == "Normal"
assert classify_phenomenon("28") == "Fog"
assert classify_phenomenon("30") == "Haze/Smoke/Dust"
assert classify_phenomenon("99") == "Active Precipitation"
assert classify_phenomenon("36") == "Other"
assert classify_phenomenon("", ix_flag="5") == "Normal"
assert classify_phenomenon(None, ix_flag="3") == "Unknown"
assert classify_phenomenon("100") == "Unknown"
assert classify_phenomenon("1.5") == "Unknown"
assert classify_phenomenon("abc") == "Unknown"

print("\nSemua pengujian SYNOP, decoding awan, dan klasifikasi WW berhasil.")
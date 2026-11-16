import sys
from pathlib import Path

import pandas as pd

# ============================================================
# 1. MENYIAPKAN IMPORT
# ============================================================
WEBSITE_DIR = Path(__file__).resolve().parents[1]

sys.path.insert(0, str(WEBSITE_DIR))

from weather_service import get_six_hour_data
from model_utils import predict_phenomenon

# ============================================================
# 2. MENGAMBIL DATA DARI DATABASE
# ============================================================
print("=" * 60)
print("PENGUJIAN PREDIKSI RANDOM FOREST")
print("=" * 60)

# Menggunakan waktu pengujian sebelumnya
selected_wib = "2025-01-01 07:00:00+07:00"

print("\nMengambil data observasi dari database...")

df = get_six_hour_data(selected_wib)

if df.empty:
    raise ValueError(
        "Data observasi tidak ditemukan di database."
    )

print(f"Jumlah data tersedia: {len(df)}")

# ============================================================
# 3. MEMILIH DATA YANG LENGKAP
# ============================================================
required_columns = [
    "data_timestamp",
    "wind_speed_ff",
    "wind_dir_deg_dd",
    "pressure_qff_mb_derived",
    "temp_drybulb_c_tttttt",
    "temp_dewpoint_c_tdtdtd",
    "relative_humidity_pc",
    "cloud_low_cover_1",
    "cloud_cover_oktas_m",
    "visibility_vv"
]

# Memastikan seluruh kolom tersedia
missing_columns = [
    col for col in required_columns
    if col not in df.columns
]

if missing_columns:
    raise ValueError(
        f"Kolom tidak tersedia: {missing_columns}"
    )

# Memilih baris dengan parameter lengkap
complete_data = df.dropna(
    subset=required_columns
)

if complete_data.empty:
    raise ValueError(
        "Tidak ada observasi dengan parameter lengkap "
        "untuk diuji."
    )

# Mengambil observasi paling akhir
data = complete_data.iloc[-1]

print("\nData observasi yang digunakan:")
print("Timestamp UTC:", data["data_timestamp"])

# ============================================================
# 4. MELAKUKAN PREDIKSI
# ============================================================
print("\nMenjalankan prediksi Random Forest...")

result = predict_phenomenon(data)

# ============================================================
# 5. MENAMPILKAN HASIL PREDIKSI
# ============================================================
print("\n" + "=" * 60)
print("HASIL PREDIKSI")
print("=" * 60)

print(
    "Fenomena Prediksi :",
    result["predicted_class"]
)

print(
    "Label Prediksi    :",
    result["predicted_label"]
)

print(
    "Confidence        :",
    f"{result['confidence']:.2%}"
)

# ============================================================
# 6. MENAMPILKAN PROBABILITAS SETIAP KELAS
# ============================================================
print("\nProbabilitas setiap kelas:")

for phenomenon, probability in result[
    "probabilities"
].items():

    print(
        f"{phenomenon:<30} : {probability:.2%}"
    )

# ============================================================
# 7. MENAMPILKAN 13 FITUR MODEL
# ============================================================
print("\n" + "=" * 60)
print("FITUR YANG DIGUNAKAN MODEL")
print("=" * 60)

print(result["features"].T)

print("\nPengujian selesai.")
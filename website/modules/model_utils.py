import joblib
import numpy as np
import pandas as pd

from pathlib import Path
from functools import lru_cache

# ============================================================
# 1. KONFIGURASI PATH MODEL
# ============================================================
BASE_DIR = Path(__file__).resolve().parents[2]

MODEL_PATH = (
    BASE_DIR
    / "model"
    / "weather_phenomena_rf_model.joblib"
)

# ============================================================
# 2. MEMUAT MODEL DAN METADATA
# ============================================================
@lru_cache(maxsize=1)
def load_model():
    """
    Memuat model Random Forest beserta metadata
    dari file weather_phenomena_rf_model.joblib.
    """

    if not MODEL_PATH.exists():
        raise FileNotFoundError(
            f"File model tidak ditemukan: {MODEL_PATH}"
        )

    model_data = joblib.load(MODEL_PATH)

    if not isinstance(model_data, dict):
        raise TypeError(
            "Format file model tidak sesuai. "
            "File seharusnya berisi dictionary."
        )

    required_keys = [
        "model",
        "selected_features",
        "label_map"
    ]

    missing_keys = [
        key for key in required_keys
        if key not in model_data
    ]

    if missing_keys:
        raise KeyError(
            f"Metadata model tidak lengkap: {missing_keys}"
        )

    model = model_data["model"]
    selected_features = model_data["selected_features"]
    label_map = model_data["label_map"]

    return model, selected_features, label_map

# ============================================================
# 3. FEATURE ENGINEERING
# ============================================================
def build_features(
    data,
    selected_features,
    input_timezone="UTC"
):
    """
    Mengolah satu data observasi menjadi 13 fitur
    yang dibutuhkan oleh model Random Forest.
    """
    data = pd.Series(data).copy()

    if "data_timestamp" not in data.index or pd.isna(data["data_timestamp"]):
        raise ValueError("Kolom data_timestamp belum tersedia.")

    timestamp = pd.Timestamp(data["data_timestamp"])
    if timestamp.tzinfo is None:
        timestamp = timestamp.tz_localize(input_timezone)

    datetime_wib = timestamp.tz_convert("Asia/Jakarta")

    # Jika tutupan awan total 0 okta (cerah), grup 8 tidak dikirim di SYNOP -> awan rendah = 0
    if (
        pd.notna(data.get("cloud_cover_oktas_m"))
        and int(float(data["cloud_cover_oktas_m"])) == 0
        and pd.isna(data.get("cloud_low_cover_1"))
    ):
        data["cloud_low_cover_1"] = 0

    # Kolom yang wajib terisi penuh
    strict_required_columns = [
        "wind_speed_ff",
        "pressure_qff_mb_derived",
        "temp_drybulb_c_tttttt",
        "temp_dewpoint_c_tdtdtd",
        "relative_humidity_pc",
        "cloud_low_cover_1",
        "cloud_cover_oktas_m",
        "visibility_vv",
    ]

    # Kolom yang wajib ada di DataFrame, tapi boleh NaN (misal dd=99 arah angin variabel)
    all_expected_columns = strict_required_columns + ["wind_dir_deg_dd"]

    missing_columns = [
        col for col in all_expected_columns if col not in data.index
    ]
    if missing_columns:
        raise ValueError(f"Kolom belum tersedia: {missing_columns}")

    if data[strict_required_columns].isna().any():
        missing_values = (
            data[strict_required_columns]
            .index[data[strict_required_columns].isna()]
            .tolist()
        )
        raise ValueError(
            f"Data observasi belum lengkap. Kolom yang kosong: {missing_values}"
        )

    hour = int(datetime_wib.hour)
    wind_speed = float(data["wind_speed_ff"])

    # Jika arah angin kosong (kode SYNOP dd=99 / variabel), beri komponen vektor netral (0.0)
    if pd.isna(data["wind_dir_deg_dd"]):
        wind_dir_sin = 0.0
        wind_dir_cos = 0.0
    else:
        wind_dir_rad = np.deg2rad(float(data["wind_dir_deg_dd"]))
        wind_dir_sin = float(np.sin(wind_dir_rad))
        wind_dir_cos = float(np.cos(wind_dir_rad))

    features = {
        "wind_speed_ff": wind_speed,
        "wind_dir_sin": wind_dir_sin,
        "wind_dir_cos": wind_dir_cos,
        "is_calm": int(wind_speed == 0),
        "pressure_qff_mb_derived": float(data["pressure_qff_mb_derived"]),
        "temp_drybulb_c_tttttt": float(data["temp_drybulb_c_tttttt"]),
        "temp_dewpoint_c_tdtdtd": float(data["temp_dewpoint_c_tdtdtd"]),
        "relative_humidity_pc": float(data["relative_humidity_pc"]),
        "cloud_low_cover_1": float(data["cloud_low_cover_1"]),
        "cloud_cover_oktas_m": float(data["cloud_cover_oktas_m"]),
        "visibility_vv": float(data["visibility_vv"]),
        "hour_sin": float(np.sin(2 * np.pi * hour / 24)),
        "hour_cos": float(np.cos(2 * np.pi * hour / 24)),
    }

    return pd.DataFrame([features], columns=selected_features)

# ============================================================
# 4. PREDIKSI FENOMENA VISIBILITY
# ============================================================
def predict_phenomenon(data):
    """
    Melakukan prediksi fenomena berdasarkan
    satu data observasi SYNOP.

    Returns
    -------
    dict
        predicted_class   : nama fenomena hasil prediksi
        predicted_label   : nilai numerik kelas
        confidence        : probabilitas kelas prediksi
        probabilities     : probabilitas seluruh kelas
        features          : 13 fitur yang digunakan model
    """

    # Memuat model dan metadata
    model, selected_features, label_map = load_model()

    # Membuat fitur
    features_df = build_features(
        data=data,
        selected_features=selected_features,
        input_timezone="UTC"
    )

    # Melakukan prediksi
    prediction = model.predict(features_df)[0]

    # Mengubah label numerik menjadi nama fenomena
    reverse_label_map = {
        value: key
        for key, value in label_map.items()
    }

    if prediction not in reverse_label_map:
        raise ValueError(
            f"Label prediksi tidak ditemukan: {prediction}"
        )

    predicted_class = reverse_label_map[prediction]

    # Mengambil probabilitas setiap kelas
    probabilities_raw = model.predict_proba(
        features_df
    )[0]

    probabilities = {}

    for class_id, probability in zip(
        model.classes_,
        probabilities_raw
    ):
        class_name = reverse_label_map.get(
            class_id,
            f"Unknown ({class_id})"
        )

        probabilities[class_name] = float(
            probability
        )

    # Mengurutkan probabilitas dari terbesar
    probabilities = dict(
        sorted(
            probabilities.items(),
            key=lambda item: item[1],
            reverse=True
        )
    )

    # Mengambil confidence kelas prediksi
    confidence = probabilities[predicted_class]

    return {
        "predicted_class": predicted_class,
        "predicted_label": int(prediction),
        "confidence": confidence,
        "probabilities": probabilities,
        "features": features_df
    }

# ============================================================
# 5. PENGUJIAN SEDERHANA
# ============================================================
if __name__ == "__main__":

    model, selected_features, label_map = load_model()

    print("=" * 55)
    print("MODEL RANDOM FOREST BERHASIL DIMUAT")
    print("=" * 55)

    print("\nJumlah fitur:", len(selected_features))
    print("Daftar kelas:", list(label_map.keys()))

    print("\nParameter model:")
    print("Jumlah estimator:", model.n_estimators)
    print("Max depth:", model.max_depth)
    print("Class weight:", model.class_weight)

    print("\nStatus model: Siap digunakan.")
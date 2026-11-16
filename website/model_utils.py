import joblib
import numpy as np
import pandas as pd

from pathlib import Path
from functools import lru_cache

# ============================================================
# 1. KONFIGURASI PATH MODEL
# ============================================================
BASE_DIR = Path(__file__).resolve().parent.parent

MODEL_PATH = (
    BASE_DIR
    / "model"
    / "visibility_rf_model.pkl"
)

# ============================================================
# 2. MEMUAT MODEL DAN METADATA
# ============================================================
@lru_cache(maxsize=1)
def load_model():
    """
    Memuat model Random Forest beserta metadata
    dari file visibility_rf_model.pkl.
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

    # Mengubah input menjadi Series
    data = pd.Series(data)

    # Memeriksa timestamp
    if "data_timestamp" not in data.index:
        raise ValueError(
            "Kolom data_timestamp belum tersedia."
        )

    timestamp = pd.Timestamp(
        data["data_timestamp"]
    )

    # Mengonversi timestamp ke WIB
    if timestamp.tzinfo is None:
        timestamp = timestamp.tz_localize(
            input_timezone
        )

    datetime_wib = timestamp.tz_convert(
        "Asia/Jakarta"
    )

    # Kolom yang dibutuhkan
    required_columns = [
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

    # Memeriksa keberadaan kolom
    missing_columns = [
        col for col in required_columns
        if col not in data.index
    ]

    if missing_columns:
        raise ValueError(
            f"Kolom belum tersedia: {missing_columns}"
        )

    # Memeriksa missing value
    if data[required_columns].isna().any():
        missing_values = data[
            required_columns
        ].index[
            data[required_columns].isna()
        ].tolist()

        raise ValueError(
            "Data observasi belum lengkap. "
            f"Kolom yang kosong: {missing_values}"
        )

    # Mengambil jam berdasarkan waktu WIB
    hour = datetime_wib.hour

    # Feature Engineering
    features = {
        "wind_speed_ff": data["wind_speed_ff"],

        "wind_dir_sin": np.sin(
            np.deg2rad(data["wind_dir_deg_dd"])
        ),

        "wind_dir_cos": np.cos(
            np.deg2rad(data["wind_dir_deg_dd"])
        ),

        "is_calm": int(
            data["wind_speed_ff"] == 0
        ),

        "pressure_qff_mb_derived":
            data["pressure_qff_mb_derived"],

        "temp_drybulb_c_tttttt":
            data["temp_drybulb_c_tttttt"],

        "temp_dewpoint_c_tdtdtd":
            data["temp_dewpoint_c_tdtdtd"],

        "relative_humidity_pc":
            data["relative_humidity_pc"],

        "cloud_low_cover_1":
            data["cloud_low_cover_1"],

        "cloud_cover_oktas_m":
            data["cloud_cover_oktas_m"],

        "visibility_vv":
            data["visibility_vv"],

        "hour_sin": np.sin(
            2 * np.pi * hour / 24
        ),

        "hour_cos": np.cos(
            2 * np.pi * hour / 24
        )
    }

    # Menyesuaikan urutan fitur dengan model
    features_df = pd.DataFrame(
        [features],
        columns=selected_features
    )

    return features_df

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
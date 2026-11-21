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
    / "weather_phenomena_lgbm_model.joblib"
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
RAW_COLS = [
    "wind_speed_ff",
    "wind_dir_deg_dd",
    "pressure_qff_mb_derived",
    "temp_drybulb_c_tttttt",
    "temp_dewpoint_c_tdtdtd",
    "relative_humidity_pc",
    "cloud_low_cover_oktas",
    "cloud_med_cover_oktas",
    "visibility_vv",
]

CLOUD_COLS = ["cloud_low_cover_oktas", "cloud_med_cover_oktas"]

SENSOR_COLS = [
    "wind_speed_ff",
    "pressure_qff_mb_derived",
    "temp_drybulb_c_tttttt",
    "temp_dewpoint_c_tdtdtd",
    "relative_humidity_pc",
    "visibility_vv",
]

IMPUTE_VALUES = {
    "cloud_low_cover_oktas": 3.0,
    "cloud_med_cover_oktas": 5.0,
}

LAG_BASE_COLS = [
    "wind_dir_sin",
    "wind_dir_cos",
    "wind_speed_ff",
    "visibility_vv",
    "pressure_qff_mb_derived",
    "temp_drybulb_c_tttttt",
    "temp_dewpoint_c_tdtdtd",
    "relative_humidity_pc",
    "cloud_low_cover_oktas",
    "cloud_med_cover_oktas",
]

DIFF_COLS = {
    "visibility_diff": "visibility_vv",
    "temp_drybulb_diff": "temp_drybulb_c_tttttt",
    "rh_diff": "relative_humidity_pc",
    "pressure_diff": "pressure_qff_mb_derived",
    "wind_speed_diff": "wind_speed_ff",
}

def build_feature_table(history):
    """
    Membuat semua kandidat fitur untuk setiap jam pada riwayat observasi.
    history: DataFrame hasil get_hours_data (data_timestamp = UTC naive).
    Jam yang tidak ada laporannya tetap muncul sebagai baris NaN,
    sehingga lag tidak bergeser ke jam yang salah.
    """
    df = history.copy()
    df["data_timestamp"] = pd.to_datetime(df["data_timestamp"])
    df = (
        df.drop_duplicates("data_timestamp")
        .set_index("data_timestamp")
        .sort_index()
    )

    full_index = pd.date_range(df.index.min(), df.index.max(), freq="h")
    df = df.reindex(full_index)

    num = pd.DataFrame(index=df.index)
    for col in RAW_COLS:
        if col not in df.columns:
            raise ValueError(f"Kolom belum tersedia: {col}")
        num[col] = pd.to_numeric(df[col], errors="coerce").astype("float64")

    # Catat laporan asli SEBELUM interpolasi
    has_report = num["wind_speed_ff"].notna()
    observed_ok = num[SENSOR_COLS].notna().all(axis=1)

    # Celah pendek (maks 2 jam, di antara dua jam yang ada datanya)
    num[SENSOR_COLS] = num[SENSOR_COLS].interpolate(limit=3, limit_area="inside")

    # Imputasi awan: ffill dulu, sisanya median data training
    for col in CLOUD_COLS:
        num[col] = num[col].ffill(limit=3).fillna(IMPUTE_VALUES[col])

    feats = num.copy()
    feats["observed_ok"] = observed_ok

    # Arah angin: 0.0 hanya jika laporan ada tapi arah variabel (dd=99)
    rad = np.deg2rad(num["wind_dir_deg_dd"])
    variable = rad.isna() & has_report
    feats["wind_dir_sin"] = np.sin(rad).mask(variable, 0.0)
    feats["wind_dir_cos"] = np.cos(rad).mask(variable, 0.0)
    feats[["wind_dir_sin", "wind_dir_cos"]] = feats[
        ["wind_dir_sin", "wind_dir_cos"]
    ].interpolate(limit=3, limit_area="inside")

    feats["is_calm"] = (num["wind_speed_ff"] == 0).astype(int)

    # Jam lokal (WIB)
    hour = (
        feats.index.tz_localize("UTC").tz_convert("Asia/Jakarta").hour.to_numpy()
    )
    feats["hour_sin"] = np.sin(2 * np.pi * hour / 24)
    feats["hour_cos"] = np.cos(2 * np.pi * hour / 24)

    # Lag 1-3 jam
    for col in LAG_BASE_COLS:
        for k in (1, 2, 3):
            feats[f"{col}_lag{k}"] = feats[col].shift(k)

    # Selisih terhadap 1 dan 3 jam sebelumnya
    for name, col in DIFF_COLS.items():
        for n in (1, 3):
            feats[f"{name}_{n}"] = feats[col] - feats[col].shift(n)

    return feats

def build_features(history, selected_features, target_timestamp=None):
    """
    Mengambil fitur untuk satu jam (default: jam terakhir pada history).
    """
    table = build_feature_table(history)

    if target_timestamp is None:
        target = table.index[-1]
    else:
        target = pd.Timestamp(target_timestamp)
        if target.tzinfo is not None:
            target = target.tz_convert("UTC").tz_localize(None)

    if target not in table.index:
        raise ValueError(f"Jam {target} tidak ada pada riwayat observasi.")

    if not bool(table.loc[target, "observed_ok"]):
        raise ValueError(
            f"Laporan jam {target} (UTC) tidak lengkap, prediksi tidak dilakukan."
        )

    unknown = [f for f in selected_features if f not in table.columns]
    if unknown:
        raise ValueError(f"Fitur model tidak tersedia: {unknown}")

    row = table.loc[[target], list(selected_features)]

    empty = row.columns[row.isna().any()].tolist()
    if empty:
        raise ValueError(
            f"Observasi atau riwayat jam sebelumnya belum lengkap. "
            f"Fitur kosong: {empty}"
        )

    return row

# ============================================================
# 4. PREDIKSI FENOMENA VISIBILITY
# ============================================================
def predict_phenomenon(history, target_timestamp=None):
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
            history=history,
            selected_features=selected_features,
            target_timestamp=target_timestamp,
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
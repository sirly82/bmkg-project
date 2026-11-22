import sys
from functools import lru_cache
from pathlib import Path

WEBSITE_DIR = Path(__file__).resolve().parents[1]
if str(WEBSITE_DIR) not in sys.path:
    sys.path.insert(0, str(WEBSITE_DIR))

import joblib
import numpy as np
import pandas as pd

from modules.synop_utils import PHENOMENON_CLASSES, classify_phenomenon

# ============================================================
# 1. KONFIGURASI PATH MODEL
# ============================================================
BASE_DIR = Path(__file__).resolve().parents[2]
CLASSIFIER_MODEL_PATH = (
    BASE_DIR
    / "model"
    / "weather_phenomena_lgbm_model.joblib"
)
FORECAST_MODEL_PATH = (
    BASE_DIR
    / "model"
    / "weather_phenomena_xgb_1h.joblib"
)
# Alias kompatibilitas dengan kode lama
MODEL_PATH = CLASSIFIER_MODEL_PATH

# ============================================================
# KONFIGURASI VALIDASI FITUR RIWAYAT (LAG & DIFF)
# ============================================================
# False = wajib memiliki 3 jam riwayat lengkap (t-1 s.d. t-3), tidak boleh NaN
# True  = mengizinkan fitur lag/diff bernilai NaN (ditangani native oleh LightGBM & XGBoost)
ALLOW_LAG_NAN = False
LAG_SUFFIXES = ("_lag1", "_lag2", "_lag3", "_diff_1", "_diff_3")

# ============================================================
# 2. MEMUAT MODEL DAN METADATA
# ============================================================
def _load_joblib_bundle(model_path: Path, model_label: str):
    if not model_path.exists():
        raise FileNotFoundError(
            f"File {model_label} tidak ditemukan: {model_path}"
        )

    model_data = joblib.load(model_path)

    if not isinstance(model_data, dict):
        raise TypeError(
            f"Format file {model_label} tidak sesuai. "
            "File seharusnya berisi dictionary."
        )

    required_keys = ["model", "selected_features", "label_map"]
    missing_keys = [key for key in required_keys if key not in model_data]

    if missing_keys:
        raise KeyError(
            f"Metadata {model_label} tidak lengkap: {missing_keys}"
        )

    return (
        model_data["model"],
        model_data["selected_features"],
        model_data["label_map"],
    )

@lru_cache(maxsize=1)
def load_classifier_model():
    """
    Memuat model LightGBM (52 fitur) beserta metadata untuk
    klasifikasi fenomena cuaca pada waktu observasi (t).
    """
    return _load_joblib_bundle(CLASSIFIER_MODEL_PATH, "model klasifikasi (t)")

@lru_cache(maxsize=1)
def load_forecast_model():
    """
    Memuat model XGBoost (59 fitur) beserta metadata untuk
    prediksi fenomena cuaca 1 jam ke depan (t+1).
    """
    return _load_joblib_bundle(FORECAST_MODEL_PATH, "model prediksi (t+1)")

def load_model():
    """Alias kompatibilitas untuk memuat model klasifikasi (t)."""
    return load_classifier_model()

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
    Membuat fitur dasar, lag (1-3 jam), dan selisih (1 & 3 jam)
    untuk setiap jam pada riwayat observasi.
    history: DataFrame observasi (data_timestamp = UTC naive).
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

    # Celah pendek (maks 3 jam, di antara dua jam yang ada datanya)
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

    # Simpan informasi fenomena aktual & kode ww untuk kebutuhan model t+1
    if "phenomenon" in df.columns:
        feats["phenomenon"] = df["phenomenon"]
    if "weather_code_ww" in df.columns:
        feats["weather_code_ww"] = df["weather_code_ww"]
    if "ix_flag" in df.columns:
        feats["ix_flag"] = df["ix_flag"]

    return feats

def _resolve_target_timestamp(table, target_timestamp=None):
    if target_timestamp is None:
        target = table.index[-1]
    else:
        target = pd.Timestamp(target_timestamp)
        if target.tzinfo is not None:
            target = target.tz_convert("UTC").tz_localize(None)

    waktu_str = f"{target.strftime('%d-%m-%Y')} pukul {target.strftime('%H:%M')} UTC"

    if target not in table.index:
        raise ValueError(f"Data observasi pada {waktu_str} tidak ditemukan pada riwayat.")

    if not bool(table.loc[target, "observed_ok"]):
        raise ValueError(
            f"Data parameter meteorologi utama pada {waktu_str} tidak lengkap."
        )

    return target

def _validate_feature_row(row, selected_features, target):
    """Memvalidasi kelengkapan fitur sesuai pengaturan global ALLOW_LAG_NAN."""
    if ALLOW_LAG_NAN:
        base_cols = [
            f for f in selected_features if not f.endswith(LAG_SUFFIXES)
        ]
        empty = [c for c in base_cols if row[c].isna().any()]
        if empty:
            waktu_str = f"{target.strftime('%d-%m-%Y')} pukul {target.strftime('%H:%M')} UTC"
            raise ValueError(
                f"Parameter observasi utama pada {waktu_str} tidak lengkap: {empty}"
            )
    else:
        empty = row[list(selected_features)].columns[
            row[list(selected_features)].isna().any()
        ].tolist()
        if empty:
            raise ValueError(
                f"Observasi atau riwayat jam sebelumnya belum lengkap. "
                f"Fitur kosong: {empty}"
            )


def build_features(history, selected_features, target_timestamp=None):
    """
    Mengambil 52 fitur untuk klasifikasi fenomena pada satu jam (t).
    """
    table = build_feature_table(history)
    target = _resolve_target_timestamp(table, target_timestamp)

    unknown = [f for f in selected_features if f not in table.columns]
    if unknown:
        raise ValueError(f"Fitur model klasifikasi tidak tersedia: {unknown}")

    row = table.loc[[target], list(selected_features)]
    _validate_feature_row(row, selected_features, target)

    return row

def _resolve_current_phenomenon(target_row, label_map, override_phenomenon=None):
    """
    Menentukan kategori fenomena saat ini (t) sebagai fitur one-hot model t+1.
    """
    valid_classes = set(label_map.keys()) | set(PHENOMENON_CLASSES)

    if override_phenomenon is not None:
        phenom = str(override_phenomenon).strip()
        if phenom in label_map:
            return phenom, "classified_fallback"
        raise ValueError(f"Kategori fenomena fallback tidak dikenal: {phenom}")

    if "phenomenon" in target_row.index and pd.notna(target_row["phenomenon"]):
        phenom = str(target_row["phenomenon"]).strip()
        if phenom in label_map:
            return phenom, "synop_actual"
        if phenom != "Unknown" and phenom not in valid_classes:
            raise ValueError(f"Kategori fenomena tidak dikenal: {phenom}")

    ww_col = None
    for candidate in ("weather_code_ww", "present_weather_ww"):
        if candidate in target_row.index and pd.notna(target_row[candidate]):
            ww_col = candidate
            break

    if ww_col is not None:
        ix_val = target_row["ix_flag"] if "ix_flag" in target_row.index else None
        phenom = classify_phenomenon(target_row[ww_col], ix_flag=ix_val)
        if phenom in label_map:
            return phenom, "synop_ww"

    raise ValueError(
        "Fenomena cuaca saat ini (t) tidak tersedia atau bernilai 'Unknown'."
    )

def build_forecast_features(
    history,
    selected_features,
    label_map,
    target_timestamp=None,
    override_phenomenon=None,
):
    """
    Mengambil 59 fitur (52 fitur observasi/lag/delta + 7 fitur one-hot now_<phenomenon>)
    untuk memprediksi fenomena cuaca 1 jam ke depan (t+1).
    """
    table = build_feature_table(history)
    target = _resolve_target_timestamp(table, target_timestamp)

    target_row = table.loc[target]
    curr_phenom, phenom_source = _resolve_current_phenomenon(
        target_row=target_row,
        label_map=label_map,
        override_phenomenon=override_phenomenon,
    )

    row = table.loc[[target]].copy()

    # Tambahkan 7 fitur one-hot kondisi cuaca saat ini (t)
    for phenom_name in label_map.keys():
        col_name = "now_" + phenom_name.replace("/", "_").replace(" ", "_")
        row[col_name] = int(curr_phenom == phenom_name)

    unknown = [f for f in selected_features if f not in row.columns]
    if unknown:
        raise ValueError(f"Fitur model prediksi (t+1) tidak tersedia: {unknown}")

    ordered_row = row[list(selected_features)]
    _validate_feature_row(ordered_row, selected_features, target)

    return ordered_row, curr_phenom, phenom_source

# ============================================================
# 4. HELPER INFERENSI PROBABILITAS
# ============================================================
def _run_model_inference(model, features_df, label_map):
    prediction = int(model.predict(features_df)[0])

    reverse_label_map = {value: key for key, value in label_map.items()}
    if prediction not in reverse_label_map:
        raise ValueError(f"Label prediksi tidak ditemukan: {prediction}")

    predicted_class = reverse_label_map[prediction]
    probabilities_raw = model.predict_proba(features_df)[0]

    probabilities = {}
    for class_id, probability in zip(model.classes_, probabilities_raw):
        class_name = reverse_label_map.get(
            int(class_id), f"Unknown ({class_id})"
        )
        probabilities[class_name] = float(probability)

    probabilities = dict(
        sorted(
            probabilities.items(),
            key=lambda item: item[1],
            reverse=True,
        )
    )

    return {
        "predicted_class": predicted_class,
        "predicted_label": prediction,
        "confidence": probabilities[predicted_class],
        "probabilities": probabilities,
        "features": features_df,
    }

# ============================================================
# 5. KLASIFIKASI (t) DAN PREDIKSI (t+1)
# ============================================================
def classify_phenomenon_at(history, target_timestamp=None):
    """
    Mengklasifikasikan fenomena cuaca pada jam observasi (t)
    menggunakan model LightGBM (52 fitur).
    """
    model, selected_features, label_map = load_classifier_model()

    features_df = build_features(
        history=history,
        selected_features=selected_features,
        target_timestamp=target_timestamp,
    )

    result = _run_model_inference(model, features_df, label_map)
    result["timestamp_utc"] = features_df.index[0]
    return result

def predict_phenomenon(history, target_timestamp=None):
    """Alias kompatibilitas untuk klasifikasi fenomena pada jam observasi (t)."""
    return classify_phenomenon_at(
        history=history,
        target_timestamp=target_timestamp,
    )

def predict_next_hour_phenomenon(
    history,
    target_timestamp=None,
    fallback_to_classified=True,
):
    """
    Memprediksi fenomena cuaca 1 jam ke depan (t+1) berdasarkan
    observasi & fenomena pada jam t menggunakan model XGBoost (59 fitur).
    """
    model, selected_features, label_map = load_forecast_model()

    try:
        features_df, curr_phenom, phenom_source = build_forecast_features(
            history=history,
            selected_features=selected_features,
            label_map=label_map,
            target_timestamp=target_timestamp,
            override_phenomenon=None,
        )
    except ValueError as err:
        if not fallback_to_classified or "Unknown" not in str(err):
            raise
        classified = classify_phenomenon_at(
            history=history,
            target_timestamp=target_timestamp,
        )
        features_df, curr_phenom, phenom_source = build_forecast_features(
            history=history,
            selected_features=selected_features,
            label_map=label_map,
            target_timestamp=target_timestamp,
            override_phenomenon=classified["predicted_class"],
        )

    result = _run_model_inference(model, features_df, label_map)
    base_ts = features_df.index[0]
    result["base_timestamp_utc"] = base_ts
    result["forecast_timestamp_utc"] = base_ts + pd.Timedelta(hours=1)
    result["input_phenomenon_t"] = curr_phenom
    result["input_phenomenon_source"] = phenom_source
    return result


# ============================================================
# 6. PENGUJIAN SEDERHANA
# ============================================================
if __name__ == "__main__":
    clf_model, clf_features, clf_labels = load_classifier_model()
    print("=" * 60)
    print("1. MODEL KLASIFIKASI (t) - LIGHTGBM BERHASIL DIMUAT")
    print("=" * 60)
    print("Jumlah fitur :", len(clf_features))
    print("Daftar kelas :", list(clf_labels.keys()))
    print("Estimators   :", getattr(clf_model, "n_estimators", "-"))
    print("Max depth    :", getattr(clf_model, "max_depth", "-"))

    fc_model, fc_features, fc_labels = load_forecast_model()
    print("\n" + "=" * 60)
    print("2. MODEL PREDIKSI (t+1) - XGBOOST BERHASIL DIMUAT")
    print("=" * 60)
    print("Jumlah fitur :", len(fc_features))
    print("Daftar kelas :", list(fc_labels.keys()))
    print("Estimators   :", getattr(fc_model, "n_estimators", "-"))
    print("Max depth    :", getattr(fc_model, "max_depth", "-"))
    print("Fitur now_*  :", [f for f in fc_features if f.startswith("now_")])

    print("\nStatus kedua model: Siap digunakan.")
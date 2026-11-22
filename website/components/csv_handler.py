from pathlib import Path
import pandas as pd
import streamlit as st

from modules.database import COLUMNS
from modules.model_utils import (
    ALLOW_LAG_NAN,
    LAG_SUFFIXES,
    build_feature_table,
    classify_phenomenon_at,
    predict_next_hour_phenomenon,
)

# Cari folder bmkg-dataset di root project (bmkg-project/bmkg-dataset)
PROJECT_DIR = Path(__file__).resolve().parents[2]
DATASET_DIR = PROJECT_DIR / "bmkg-dataset"
if not DATASET_DIR.exists():
    ALT_DATASET_DIR = Path(__file__).resolve().parents[1] / "bmkg-dataset"
    if ALT_DATASET_DIR.exists():
        DATASET_DIR = ALT_DATASET_DIR

def _to_iso(ts):
    if ts is None or pd.isna(ts):
        return None
    return pd.Timestamp(ts).isoformat()

def list_dataset_files():
    """Mengambil daftar file clean*.csv di dalam folder bmkg-dataset/."""
    if not DATASET_DIR.exists():
        return []
    files = sorted(
        p.relative_to(DATASET_DIR).as_posix()
        for p in DATASET_DIR.rglob("clean*.csv")
        if p.is_file()
    )
    return files

def get_dataset_file_path(rel_path):
    return DATASET_DIR / rel_path

@st.cache_data(show_spinner=False)
def _load_and_normalize_csv(file_path_str, file_mtime):
    """Membaca CSV dataset internal dan menyamakan skema kolomnya dengan SYNOP."""
    df = pd.read_csv(file_path_str, low_memory=False)

    if "data_timestamp" not in df.columns:
        raise ValueError("Kolom 'data_timestamp' tidak ditemukan di file CSV.")

    # Penyesuaian nama kolom lama jika ada
    if "cloud_low_cover_1" in df.columns and "cloud_low_cover_oktas" not in df.columns:
        df = df.rename(columns={"cloud_low_cover_1": "cloud_low_cover_oktas"})

    # Penyesuaian nama kolom dari format dataset internal BMKG ke skema standar
    column_aliases = {
        "cloud_low_cover_1": "cloud_low_cover_oktas",
        "present_weather_ww": "weather_code_ww",
        "weather_indicator_ix": "ix_flag",
    }
    for src, dst in column_aliases.items():
        if src in df.columns:
            if dst not in df.columns:
                df = df.rename(columns={src: dst})
            else:
                df[dst] = df[dst].fillna(df[src])

    # Pastikan seluruh kolom standar tersedia agar kompatibel dengan tampilan & model
    for col in COLUMNS:
        if col not in df.columns:
            df[col] = None

    df["data_timestamp"] = pd.to_datetime(
        df["data_timestamp"],
        errors="coerce",
        utc=True,
    )
    df = df.dropna(subset=["data_timestamp"]).copy()

    if df.empty:
        raise ValueError("Tidak ada baris dengan format 'data_timestamp' yang valid.")

    df = (
        df.sort_values("data_timestamp")
        .drop_duplicates(subset=["data_timestamp"], keep="last")
        .reset_index(drop=True)
    )
    return df

def load_dataset_df(rel_path):
    file_path = get_dataset_file_path(rel_path)
    if not file_path.exists():
        raise FileNotFoundError(f"File dataset tidak ditemukan: {rel_path}")
    return _load_and_normalize_csv(str(file_path), file_path.stat().st_mtime)

def get_dataset_time_metadata(df_csv, selected_timezone):
    """
    Menghasilkan daftar tanggal dan jam yang valid sesuai konfigurasi ALLOW_LAG_NAN,
    serta rentang timestamp dalam zona waktu lokal pilihan pengguna.
    """
    history_naive = df_csv.assign(
        data_timestamp=df_csv["data_timestamp"].dt.tz_localize(None)
    )
    feats = build_feature_table(history_naive)

    non_feature_cols = {"phenomenon", "weather_code_ww", "ix_flag", "wind_dir_deg_dd"}
    feature_cols = [c for c in feats.columns if c not in non_feature_cols]

    if ALLOW_LAG_NAN:
        base_cols = [c for c in feature_cols if not c.endswith(LAG_SUFFIXES)]
        valid_mask = feats["observed_ok"].fillna(False) & feats[base_cols].notna().all(axis=1)
        empty_msg = "Dataset tidak memiliki baris observasi dengan parameter utama yang lengkap."
    else:
        valid_mask = feats["observed_ok"].fillna(False) & feats[feature_cols].notna().all(axis=1)
        empty_msg = (
            "Dataset tidak memiliki minimal 4 jam observasi berurutan "
            "untuk membentuk riwayat lengkap (t-1 s.d. t-3)."
        )

    valid_utc_index = feats.index[valid_mask]
    if len(valid_utc_index) == 0:
        raise ValueError(empty_msg)

    valid_local = valid_utc_index.tz_localize("UTC").tz_convert(selected_timezone)
    hours_by_date = {}
    for ts in valid_local:
        d = ts.date()
        hours_by_date.setdefault(d, set()).add(int(ts.hour))

    hours_by_date = {d: sorted(hrs) for d, hrs in hours_by_date.items()}
    raw_local_series = df_csv["data_timestamp"].dt.tz_convert(selected_timezone)

    return {
        "min_date": min(hours_by_date.keys()),
        "max_date": max(hours_by_date.keys()),
        "earliest_selectable_local": valid_local.min(),
        "raw_first_local": raw_local_series.min(),
        "latest_local": valid_local.max(),
        "hours_by_date": hours_by_date,
        "allow_lag_nan": ALLOW_LAG_NAN,
    }

def _extract_actual_next_hour(df_full, forecast_utc_aware, selected_timezone):
    matched = df_full[df_full["data_timestamp"] == forecast_utc_aware]
    if matched.empty:
        return None

    row = matched.iloc[0]
    obs_utc = pd.Timestamp(row["data_timestamp"])
    obs_local = obs_utc.tz_convert(selected_timezone).tz_localize(None)

    record = {
        "data_timestamp_iso": _to_iso(obs_utc),
        "timestamp_local_iso": _to_iso(obs_local),
    }
    for col, val in row.items():
        if col in ("data_timestamp", "timestamp_local", "prediction_result"):
            continue
        if pd.isna(val):
            record[col] = None
        elif hasattr(val, "item"):
            record[col] = val.item()
        else:
            record[col] = val

    return record

def fetch_and_predict_csv(rel_path, selected_datetime, selected_timezone):
    """
    Mengambil irisan data 28 jam (t-26 s.d. t+1) dari file CSV internal,
    lalu menjalankan klasifikasi (t-23..t) dan prediksi (t+1).
    """
    df_csv = load_dataset_df(rel_path)

    ts_local = pd.Timestamp(selected_datetime)
    if ts_local.tzinfo is None:
        ts_local = ts_local.tz_localize(selected_timezone)
    else:
        ts_local = ts_local.tz_convert(selected_timezone)

    target_utc_aware = ts_local.floor("h").tz_convert("UTC")
    history_start_aware = target_utc_aware - pd.Timedelta(hours=26)
    display_start_aware = target_utc_aware - pd.Timedelta(hours=23)
    forecast_utc_aware = target_utc_aware + pd.Timedelta(hours=1)

    df_full = (
        df_csv[
            (df_csv["data_timestamp"] >= history_start_aware)
            & (df_csv["data_timestamp"] <= forecast_utc_aware)
        ]
        .copy()
        .reset_index(drop=True)
    )

    if df_full.empty:
        raise ValueError("Data observasi tidak ditemukan pada waktu yang dipilih di CSV.")

    df_full["timestamp_local"] = (
        df_full["data_timestamp"]
        .dt.tz_convert(selected_timezone)
        .dt.tz_localize(None)
    )

    history = df_full.assign(
        data_timestamp=df_full["data_timestamp"].dt.tz_localize(None)
    )

    display_df = (
        df_full[
            (df_full["data_timestamp"] >= display_start_aware)
            & (df_full["data_timestamp"] <= target_utc_aware)
        ]
        .copy()
        .reset_index(drop=True)
    )

    if display_df.empty:
        raise ValueError("Data observasi pada rentang 24 jam utama tidak tersedia di CSV.")

    # 1. Klasifikasi fenomena (t - 23 s.d. t)
    classification_results = []
    for ts in display_df["data_timestamp"].dt.tz_localize(None):
        try:
            res = classify_phenomenon_at(history, target_timestamp=ts)
            classification_results.append({
                "predicted_class": res["predicted_class"],
                "confidence": float(res["confidence"]),
                "probabilities": res["probabilities"],
                "error": None,
            })
        except Exception as error:
            classification_results.append({
                "predicted_class": None,
                "confidence": None,
                "probabilities": None,
                "error": str(error),
            })

    display_df["prediction_result"] = classification_results

    # 2. Prediksi 1 jam ke depan (t + 1)
    target_utc_naive = target_utc_aware.tz_localize(None)
    forecast_utc_naive = forecast_utc_aware.tz_localize(None)

    base_local = target_utc_aware.tz_convert(selected_timezone).tz_localize(None)
    forecast_local = forecast_utc_aware.tz_convert(selected_timezone).tz_localize(None)
    actual_next_hour = _extract_actual_next_hour(
        df_full,
        forecast_utc_aware,
        selected_timezone,
    )

    try:
        fc_res = predict_next_hour_phenomenon(
            history,
            target_timestamp=target_utc_naive,
        )
        forecast_1h = {
            "base_timestamp_utc_iso": _to_iso(target_utc_naive),
            "base_timestamp_local_iso": _to_iso(base_local),
            "forecast_timestamp_utc_iso": _to_iso(forecast_utc_naive),
            "forecast_timestamp_local_iso": _to_iso(forecast_local),
            "used_fallback": False,
            "input_phenomenon_t": fc_res["input_phenomenon_t"],
            "input_phenomenon_source": fc_res["input_phenomenon_source"],
            "predicted_class": fc_res["predicted_class"],
            "predicted_label": int(fc_res["predicted_label"]),
            "confidence": float(fc_res["confidence"]),
            "probabilities": fc_res["probabilities"],
            "actual_next_hour": actual_next_hour,
            "error": None,
        }
    except Exception as error:
        forecast_1h = {
            "base_timestamp_utc_iso": _to_iso(target_utc_naive),
            "base_timestamp_local_iso": _to_iso(base_local),
            "forecast_timestamp_utc_iso": _to_iso(forecast_utc_naive),
            "forecast_timestamp_local_iso": _to_iso(forecast_local),
            "used_fallback": False,
            "input_phenomenon_t": None,
            "input_phenomenon_source": None,
            "predicted_class": None,
            "predicted_label": None,
            "confidence": None,
            "probabilities": None,
            "actual_next_hour": actual_next_hour,
            "error": str(error),
        }

    display_df.attrs = {
        "forecast_1h": forecast_1h,
        "dataset_source": "internal",
        "dataset_file": rel_path,
    }
    return display_df
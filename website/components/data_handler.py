import pandas as pd

from modules.model_utils import (
    classify_phenomenon_at,
    predict_next_hour_phenomenon,
)
from modules.weather_service import get_hours_data, get_window_bounds

def _to_iso(ts):
    if ts is None or pd.isna(ts):
        return None
    return pd.Timestamp(ts).isoformat()

def _extract_actual_next_hour(df_full, forecast_utc_aware, selected_timezone):
    """
    Mengambil seluruh kolom observasi aktual pada jam t+1 jika sudah tersedia
    di data SYNOP (misalnya saat pengguna memilih waktu lampau).
    """
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

def fetch_and_predict(selected_datetime, selected_timezone, force_refresh=False):
    """
    Mengambil data observasi (t - 26 jam s.d. t + 1 jam), lalu:
    1. Mengklasifikasikan fenomena cuaca untuk 24 jam tampilan (t - 23 s.d. t).
    2. Memprediksi fenomena cuaca 1 jam ke depan (t + 1) berdasarkan jam terpilih (t).
    """
    bounds = get_window_bounds(
        selected_datetime=selected_datetime,
        selected_timezone=selected_timezone,
    )

    df_full = get_hours_data(
        selected_datetime,
        selected_timezone=selected_timezone,
        force_refresh=force_refresh,
    )

    if df_full is None or df_full.empty:
        raise ValueError(
            "Data observasi tidak ditemukan untuk tanggal dan jam yang dipilih."
        )

    df_full = df_full.copy()
    df_full["data_timestamp"] = pd.to_datetime(df_full["data_timestamp"], utc=True)
    df_full = df_full.sort_values("data_timestamp").reset_index(drop=True)

    # Pemeriksaan laporan SYNOP untuk debugging
    debug_columns = [
        c
        for c in ["data_timestamp", "ix_flag", "weather_code_ww", "phenomenon", "raw_synop"]
        if c in df_full.columns
    ]
    print("\n=== PEMERIKSAAN LAPORAN SYNOP ===")
    print(df_full[debug_columns].to_string(index=False))
    print("================================")

    # Riwayat lengkap (t-26 s.d. t+1) dalam UTC naive untuk fitur lag & diff
    history = df_full.assign(
        data_timestamp=df_full["data_timestamp"].dt.tz_localize(None)
    )

    # Potong tampilan utama ke rentang 24 jam (t-23 s.d. t)
    display_start_aware = pd.Timestamp(bounds["display_start_utc"], tz="UTC")
    target_utc_aware = pd.Timestamp(bounds["target_utc"], tz="UTC")

    display_df = (
        df_full[
            (df_full["data_timestamp"] >= display_start_aware)
            & (df_full["data_timestamp"] <= target_utc_aware)
        ]
        .copy()
        .reset_index(drop=True)
    )

    if display_df.empty:
        raise ValueError(
            "Data observasi pada rentang 24 jam utama tidak tersedia."
        )

    # --------------------------------------------------------
    # 1. KLASIFIKASI FENOMENA CUACA (t - 23 s.d. t)
    # --------------------------------------------------------
    classification_results = []
    for ts in display_df["data_timestamp"].dt.tz_localize(None):
        try:
            result = classify_phenomenon_at(history, target_timestamp=ts)
            classification_results.append({
                "predicted_class": result["predicted_class"],
                "confidence": float(result["confidence"]),
                "probabilities": result["probabilities"],
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

    # --------------------------------------------------------
    # 2. PREDIKSI FENOMENA 1 JAM KE DEPAN (t + 1)
    # --------------------------------------------------------
    target_utc_naive = bounds["target_utc"]
    available_up_to_target = history[history["data_timestamp"] <= target_utc_naive]

    used_fallback = False
    base_utc_naive = target_utc_naive

    if not available_up_to_target.empty:
        latest_available = available_up_to_target["data_timestamp"].iloc[-1]
        if latest_available < target_utc_naive:
            gap = target_utc_naive - latest_available
            if gap <= pd.Timedelta(hours=3):
                base_utc_naive = latest_available
                used_fallback = True

    forecast_utc_naive = base_utc_naive + pd.Timedelta(hours=1)
    forecast_utc_aware = pd.Timestamp(forecast_utc_naive, tz="UTC")

    base_local = (
        pd.Timestamp(base_utc_naive, tz="UTC")
        .tz_convert(selected_timezone)
        .tz_localize(None)
    )
    forecast_local = (
        pd.Timestamp(forecast_utc_naive, tz="UTC")
        .tz_convert(selected_timezone)
        .tz_localize(None)
    )

    actual_next_hour = _extract_actual_next_hour(
        df_full,
        forecast_utc_aware,
        selected_timezone,
    )

    try:
        fc_res = predict_next_hour_phenomenon(
            history,
            target_timestamp=base_utc_naive,
        )
        forecast_1h = {
            "base_timestamp_utc_iso": _to_iso(base_utc_naive),
            "base_timestamp_local_iso": _to_iso(base_local),
            "forecast_timestamp_utc_iso": _to_iso(forecast_utc_naive),
            "forecast_timestamp_local_iso": _to_iso(forecast_local),
            "used_fallback": used_fallback,
            "input_phenomenon_t": fc_res["input_phenomenon_t"],
            "input_phenomenon_source": fc_res["input_phenomenon_source"],
            "predicted_class": fc_res["predicted_class"],
            "predicted_label": int(fc_res["predicted_label"]),
            "confidence": float(fc_res["confidence"]),
            "probabilities": fc_res["probabilities"],
            "actual_next_hour": actual_next_hour,
            "error": None,
        }
        print(
            f"\n[Prediksi t+1] Basis {base_local} -> Target {forecast_local}: "
            f"{fc_res['predicted_class']} ({fc_res['confidence']:.2%})"
        )
    except Exception as error:
        forecast_1h = {
            "base_timestamp_utc_iso": _to_iso(base_utc_naive),
            "base_timestamp_local_iso": _to_iso(base_local),
            "forecast_timestamp_utc_iso": _to_iso(forecast_utc_naive),
            "forecast_timestamp_local_iso": _to_iso(forecast_local),
            "used_fallback": used_fallback,
            "input_phenomenon_t": None,
            "input_phenomenon_source": None,
            "predicted_class": None,
            "predicted_label": None,
            "confidence": None,
            "probabilities": None,
            "actual_next_hour": actual_next_hour,
            "error": str(error),
        }
        print(f"\n[Prediksi t+1] Gagal untuk basis {base_local}: {error}")

    # Simpan metadata dalam format JSON-serializable murni
    display_df.attrs = {
        "forecast_1h": forecast_1h,
        "window_bounds": {k: _to_iso(v) for k, v in bounds.items()},
    }

    return display_df
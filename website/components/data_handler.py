import pandas as pd

from modules.weather_service import get_hours_data
from modules.model_utils import predict_phenomenon

def fetch_and_predict(selected_datetime, selected_timezone, force_refresh=False):
    """
    Mengambil data observasi 24 jam lalu menjalankan prediksi untuk setiap jam.
    Imputasi awan dan fitur riwayat (lag/diff) ditangani di model_utils.
    """
    df = get_hours_data(
        selected_datetime,
        selected_timezone=selected_timezone,
        force_refresh=force_refresh,
    )

    if df is None or df.empty:
        raise ValueError(
            "Data observasi tidak ditemukan untuk tanggal dan jam yang dipilih."
        )

    df = df.copy()
    df["data_timestamp"] = pd.to_datetime(df["data_timestamp"], utc=True)
    df = df.sort_values("data_timestamp").reset_index(drop=True)

    # Pemeriksaan laporan SYNOP untuk debugging.
    debug_columns = [
        c for c in
        ["data_timestamp", "ix_flag", "weather_code_ww", "phenomenon", "raw_synop"]
        if c in df.columns
    ]
    print("\n=== PEMERIKSAAN LAPORAN SYNOP ===")
    print(df[debug_columns].to_string(index=False))
    print("================================")

    # Riwayat untuk model: UTC tanpa zona waktu (sama dengan model_utils)
    history = df.assign(
        data_timestamp=df["data_timestamp"].dt.tz_localize(None)
    )

    prediction_results = []
    for ts in history["data_timestamp"]:
        try:
            result = predict_phenomenon(history, target_timestamp=ts)
            prediction_results.append({
                "predicted_class": result["predicted_class"],
                "confidence": result["confidence"],
                "probabilities": result["probabilities"],
                "error": None,
            })
        except Exception as error:
            prediction_results.append({
                "predicted_class": None,
                "confidence": None,
                "probabilities": None,
                "error": str(error),
            })

    df["prediction_result"] = prediction_results
    return df
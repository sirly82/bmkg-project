import pandas as pd

from modules.weather_service import get_hours_data
from modules.model_utils import predict_phenomenon

def _prepare_cloud_columns(df):
    """
    Mengisi missing value pada dua parameter tutupan awan.

    Urutan:
    1. Memastikan kolom bertipe numerik agar aman saat ffill/fillna.
    2. Jika awan total 0 okta (cerah), awan rendah diisi 0.
    3. Menghitung modus dari data scraping asli.
    4. Mengisi nilai kosong dengan forward fill berdasarkan waktu.
    5. Mengisi sisa nilai kosong menggunakan modus dari jendela 24 jam.
    """
    cloud_columns = [
        "cloud_low_cover_1",
        "cloud_cover_oktas_m"
    ]

    missing_columns = [
        col for col in cloud_columns if col not in df.columns
    ]
    if missing_columns:
        raise ValueError(
            f"Kolom tutupan awan tidak ditemukan: {missing_columns}"
        )

    # 1. Pastikan tipe data numerik (menghindari error/warning jika semua baris NULL)
    for col in cloud_columns:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    # 2. Jika awan total = 0 okta, awan rendah pasti 0 (jangan di-ffill dari jam berawan)
    clear_sky_mask = (df["cloud_cover_oktas_m"] == 0) & (df["cloud_low_cover_1"].isna())
    df.loc[clear_sky_mask, "cloud_low_cover_1"] = 0.0

    # 3. Hitung modus sebelum forward fill
    cloud_modes = {}
    for col in cloud_columns:
        modes = df[col].mode(dropna=True)
        cloud_modes[col] = modes.iloc[0] if not modes.empty else None

    # 4. Forward fill berdasarkan urutan waktu
    df[cloud_columns] = df[cloud_columns].ffill()

    # 5. Isi sisa nilai kosong di awal jendela dengan modus 24 jam
    for col in cloud_columns:
        if cloud_modes[col] is not None:
            df[col] = df[col].fillna(cloud_modes[col])

    return df

def _prepare_meteorological_columns(df):
    """
    Mengisi kekosongan sesaat (maksimal 1 jam) pada parameter sensor utama
    agar gangguan pengiriman satu laporan tidak menggagalkan prediksi.
    """
    sensor_columns = [
        "wind_speed_ff",
        "pressure_qff_mb_derived",
        "temp_drybulb_c_tttttt",
        "temp_dewpoint_c_tdtdtd",
        "relative_humidity_pc",
        "visibility_vv",
    ]

    for col in sensor_columns:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").ffill(limit=1)

    return df

def fetch_and_predict(selected_datetime, selected_timezone, force_refresh=False):
    """
    Mengambil data observasi 24 jam, melakukan preprocessing,
    lalu menjalankan prediksi untuk setiap laporan yang tersedia.

    Fungsi ini hanya dipanggil ketika tombol pengambilan data ditekan.
    """
    with pd.option_context("mode.chained_assignment", None):
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
    df["data_timestamp"] = pd.to_datetime(
        df["data_timestamp"],
        utc=True
    )
    df = (
        df.sort_values("data_timestamp")
        .reset_index(drop=True)
    )

    df = _prepare_cloud_columns(df)
    df = _prepare_meteorological_columns(df)

    # Pemeriksaan laporan SYNOP untuk debugging.
    debug_columns = [
        "data_timestamp",
        "ix_flag",
        "weather_code_ww",
        "phenomenon",
        "raw_synop"
    ]
    available_debug_columns = [
        col for col in debug_columns if col in df.columns
    ]

    print("\n=== PEMERIKSAAN LAPORAN SYNOP ===")
    print(df[available_debug_columns].to_string(index=False))
    print("================================")

    prediction_results = []

    for _, row in df.iterrows():
        try:
            result = predict_phenomenon(row)

            prediction_results.append({
                "predicted_class": result["predicted_class"],
                "confidence": result["confidence"],
                "probabilities": result["probabilities"],
                "error": None
            })
        except Exception as error:
            prediction_results.append({
                "predicted_class": None,
                "confidence": None,
                "probabilities": None,
                "error": str(error)
            })

    df["prediction_result"] = prediction_results
    return df
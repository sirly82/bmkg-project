import pandas as pd

from modules.database import (
    get_checked_hours,
    get_reports,
    init_db,
    mark_hours_checked,
    save_reports,
)
from modules.synop_utils import scrape_synop_range


def get_window_bounds(
    selected_datetime,
    selected_timezone="Asia/Jakarta",
    display_hours=24,
    lag_buffer_hours=3,
    forecast_horizon_hours=1,
):
    """
    Menghitung batas waktu (UTC naive) untuk:
    - fetch_start_utc   : t - (display_hours - 1) - lag_buffer_hours (default: t - 26 jam)
    - display_start_utc : t - (display_hours - 1) (default: t - 23 jam)
    - target_utc        : waktu observasi terpilih (t)
    - forecast_utc      : t + forecast_horizon_hours (default: t + 1 jam)
    """
    selected_time = pd.Timestamp(selected_datetime)
    if selected_time.tzinfo is None:
        selected_time = selected_time.tz_localize(selected_timezone)

    target_utc = selected_time.tz_convert("UTC").floor("h").tz_localize(None)
    display_start_utc = target_utc - pd.Timedelta(hours=display_hours - 1)
    fetch_start_utc = display_start_utc - pd.Timedelta(hours=lag_buffer_hours)
    forecast_utc = target_utc + pd.Timedelta(hours=forecast_horizon_hours)

    return {
        "target_utc": target_utc,
        "display_start_utc": display_start_utc,
        "fetch_start_utc": fetch_start_utc,
        "forecast_utc": forecast_utc,
    }


def get_hours_data(
    selected_datetime,
    selected_timezone="Asia/Jakarta",
    force_refresh=False,
    display_hours=24,
    lag_buffer_hours=3,
    forecast_horizon_hours=1,
):
    """
    Mengambil data observasi SYNOP dari (t - 26 jam) hingga (t + 1 jam):
    - 3 jam buffer sebelum rentang 24 jam agar lag1..lag3 lengkap sejak jam pertama tampilan
    - 24 jam utama (t - 23 s.d. t) untuk klasifikasi & grafik monitoring
    - 1 jam setelah t (t + 1) untuk pembanding aktual terhadap hasil prediksi (jika tersedia)
    """
    # --------------------------------------------------------
    # 1. Hitung batas waktu dalam UTC (naive)
    # --------------------------------------------------------
    bounds = get_window_bounds(
        selected_datetime=selected_datetime,
        selected_timezone=selected_timezone,
        display_hours=display_hours,
        lag_buffer_hours=lag_buffer_hours,
        forecast_horizon_hours=forecast_horizon_hours,
    )
    start_utc = bounds["fetch_start_utc"]
    end_utc = bounds["forecast_utc"]

    required_hours = list(
        pd.date_range(
            start=start_utc,
            end=end_utc,
            freq="h",
        )
    )

    # --------------------------------------------------------
    # 2. Pastikan database tersedia
    # --------------------------------------------------------
    init_db()

    # --------------------------------------------------------
    # 3. Periksa jam yang perlu diambil dari Ogimet
    # --------------------------------------------------------
    now_utc = pd.Timestamp.now(tz="UTC").floor("h").tz_localize(None)

    if force_refresh:
        unchecked_hours = [h for h in required_hours if h <= now_utc]
    else:
        checked_hours = get_checked_hours(start_utc, end_utc)
        unchecked_hours = [
            hour
            for hour in required_hours
            if (hour not in checked_hours) and (hour <= now_utc)
        ]

    # --------------------------------------------------------
    # 4. Kelompokkan jam yang berurutan
    # --------------------------------------------------------
    groups = []
    for hour in unchecked_hours:
        if not groups:
            groups.append([hour])
        elif hour - groups[-1][-1] == pd.Timedelta(hours=1):
            groups[-1].append(hour)
        else:
            groups.append([hour])

    # Jeda aman 2 jam agar laporan yang terlambat rilis tetap bisa diambil ulang
    safe_cache_cutoff = (
        pd.Timestamp.now(tz="UTC").tz_localize(None)
        - pd.Timedelta(hours=2)
    )

    # --------------------------------------------------------
    # 5. Ambil hanya rentang yang belum diperiksa
    # --------------------------------------------------------
    for group in groups:
        group_start = group[0]
        group_end = group[-1]

        print(
            "\nMengambil data Ogimet untuk rentang:",
            group_start,
            "sampai",
            group_end,
        )

        df_new = scrape_synop_range(
            start_datetime=group_start,
            end_datetime=group_end,
        )

        found_hours = set()
        if df_new is not None and not df_new.empty:
            save_reports(df_new)
            found_hours = set(
                pd.to_datetime(df_new["data_timestamp"]).dt.floor("h")
            )

        hours_to_mark = [
            h
            for h in group
            if (h in found_hours) or (h <= safe_cache_cutoff)
        ]
        mark_hours_checked(hours_to_mark)

    # --------------------------------------------------------
    # 6. Ambil kembali seluruh data dari SQLite
    # --------------------------------------------------------
    df_result = get_reports(
        start_datetime=start_utc,
        end_datetime=end_utc,
    )

    # --------------------------------------------------------
    # 7. Tambahkan timestamp lokal & periksa ketersediaan laporan
    # --------------------------------------------------------
    if not df_result.empty:
        df_result["timestamp_local"] = (
            df_result["data_timestamp"]
            .dt.tz_localize("UTC")
            .dt.tz_convert(selected_timezone)
            .dt.tz_localize(None)
        )
        available_hours = set(
            df_result["data_timestamp"].dt.floor("h")
        )
    else:
        available_hours = set()

    missing_reports = [
        hour
        for hour in required_hours
        if hour not in available_hours
    ]

    # --------------------------------------------------------
    # 8. Informasi hasil
    # --------------------------------------------------------
    print("\nPemeriksaan window observasi selesai.")
    print("Rentang UTC                :", start_utc, "s.d.", end_utc)
    print("Jumlah jam dalam window    :", len(required_hours))
    print("Jumlah laporan tersedia    :", len(df_result))
    print("Jumlah jam tanpa laporan   :", len(missing_reports))

    return df_result
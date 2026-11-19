import pandas as pd

from modules.database import (
    get_checked_hours,
    get_reports,
    init_db,
    mark_hours_checked,
    save_reports,
)
from modules.synop_utils import scrape_synop_range

def get_hours_data(
    selected_datetime,
    selected_timezone="Asia/Jakarta",
    force_refresh=False,
):
    """
    Mengambil data observasi SYNOP selama 24 jam
    yang berakhir pada waktu pilihan pengguna.
    """
    # --------------------------------------------------------
    # 1. Konversi waktu pilihan ke UTC
    # --------------------------------------------------------
    selected_time = pd.Timestamp(selected_datetime)

    if selected_time.tzinfo is None:
        selected_time = selected_time.tz_localize(selected_timezone)

    end_utc = selected_time.tz_convert("UTC").floor("h")
    start_utc = end_utc - pd.Timedelta(hours=23)

    # 24 timestamp yang dibutuhkan (naive UTC)
    required_hours = list(
        pd.date_range(
            start=start_utc,
            end=end_utc,
            freq="h",
        ).tz_localize(None)
    )

    # --------------------------------------------------------
    # 2. Pastikan database tersedia
    # --------------------------------------------------------
    init_db()

    # --------------------------------------------------------
    # 3. Periksa jam yang sudah pernah diperiksa
    # --------------------------------------------------------
    if force_refresh:
        unchecked_hours = required_hours
    else:
        checked_hours = get_checked_hours(start_utc, end_utc)
        unchecked_hours = [
            hour
            for hour in required_hours
            if hour not in checked_hours
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

    # Batas waktu aman untuk menandai jam kosong sebagai "permanen kosong"
    # (beri jeda 2 jam dari waktu sekarang agar laporan yang telat masuk tetap bisa diambil ulang)
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

        # Tandai jam yang datanya ditemukan, ATAU jam yang sudah cukup lampau
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
    print("\nPemeriksaan 24 jam selesai.")
    print("Jumlah jam yang dibutuhkan :", len(required_hours))
    print("Jumlah laporan tersedia   :", len(df_result))
    print("Jumlah jam tanpa laporan  :", len(missing_reports))

    return df_result
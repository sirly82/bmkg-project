import pandas as pd

from modules.synop_utils import scrape_synop_range
from modules.database import (
    init_db,
    get_reports,
    get_checked_hours,
    mark_hours_checked,
    save_reports,
)

def get_hours_data(
    selected_datetime,
    selected_timezone="Asia/Jakarta",
    force_refresh=False
):
    """
    Mengambil data observasi SYNOP selama 24 jam
    yang berakhir pada waktu pilihan pengguna.

    Parameters
    ----------
    selected_datetime : datetime-like
        Waktu pilihan pengguna.

    selected_timezone : str
        Zona waktu yang digunakan jika selected_datetime
        belum memiliki informasi timezone.

    force_refresh : bool
        Jika True, ambil ulang seluruh rentang dari Ogimet.

    Returns
    -------
    pandas.DataFrame
        Data laporan SYNOP yang tersedia dalam 24 jam.
    """

    # --------------------------------------------------------
    # 1. Konversi waktu pilihan ke UTC
    # --------------------------------------------------------
    selected_time = pd.Timestamp(selected_datetime)

    if selected_time.tzinfo is None:
        selected_time = selected_time.tz_localize(
            selected_timezone
        )

    end_utc = selected_time.tz_convert("UTC").floor("h")
    start_utc = end_utc - pd.Timedelta(hours=23)

    # 24 timestamp yang dibutuhkan
    required_hours = list(
        pd.date_range(
            start=start_utc,
            end=end_utc,
            freq="h"
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
        checked_hours = get_checked_hours(
            start_utc,
            end_utc
        )
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
        elif (
            hour - groups[-1][-1]
            == pd.Timedelta(hours=1)
        ):
            groups[-1].append(hour)
        else:
            groups.append([hour])

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
            group_end
        )

        # Jika scraping mengalami exception,
        # jam tidak akan ditandai sebagai sudah diperiksa.
        df_new = scrape_synop_range(
            start_datetime=group_start,
            end_datetime=group_end
        )

        if df_new is not None and not df_new.empty:
            save_reports(df_new)

        # Tandai jam setelah scraping berhasil dijalankan.
        # Jam tanpa laporan juga dicatat.
        mark_hours_checked(group)

    # --------------------------------------------------------
    # 6. Ambil kembali seluruh data dari SQLite
    # --------------------------------------------------------
    df_result = get_reports(
        start_datetime=start_utc,
        end_datetime=end_utc
    )

    # --------------------------------------------------------
    # 7. Periksa ketersediaan laporan
    # --------------------------------------------------------
    if not df_result.empty:
        available_hours = set(
            pd.to_datetime(
                df_result["data_timestamp"],
                utc=True
            ).dt.tz_localize(None)
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
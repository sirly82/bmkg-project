import pandas as pd

from synop_utils import scrape_synop_range
from database import (
    init_db,
    get_reports,
    get_checked_hours,
    mark_hours_checked,
    save_reports,
)

def get_six_hour_data(selected_wib, force_refresh=False):
    """
    Mengambil data enam jam yang berakhir pada waktu pilihan pengguna.

    Parameters
    ----------
    selected_wib : datetime-like
        Waktu pilihan pengguna dalam WIB.

    force_refresh : bool
        Jika True, ambil ulang seluruh rentang dari Ogimet.

    Returns
    -------
    pandas.DataFrame
        Data laporan SYNOP yang tersedia dalam enam jam tersebut.
    """

    # --------------------------------------------------------
    # 1. Konversi waktu pilihan ke UTC
    # --------------------------------------------------------
    selected_wib = pd.Timestamp(selected_wib)

    if selected_wib.tzinfo is None:
        selected_wib = selected_wib.tz_localize(
            "Asia/Jakarta"
        )
    else:
        selected_wib = selected_wib.tz_convert(
            "Asia/Jakarta"
        )

    end_utc = selected_wib.tz_convert("UTC").floor("h")
    start_utc = end_utc - pd.Timedelta(hours=5)

    # Enam timestamp yang dibutuhkan.
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
            hour for hour in required_hours
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

        # Jika terjadi exception, jam tidak akan ditandai
        # sehingga dapat dicoba kembali pada pemanggilan berikutnya.
        df_new = scrape_synop_range(
            start_datetime=group_start,
            end_datetime=group_end
        )

        if df_new is not None and not df_new.empty:
            save_reports(df_new)

        # Tandai jam setelah proses scraping berhasil dijalankan.
        # Ini juga mencatat jam yang tidak memiliki laporan.
        mark_hours_checked(group)

    # --------------------------------------------------------
    # 6. Ambil kembali seluruh data dari SQLite
    # --------------------------------------------------------

    df_result = get_reports(
        start_datetime=start_utc,
        end_datetime=end_utc
    )

    # --------------------------------------------------------
    # 7. Informasi hasil
    # --------------------------------------------------------

    available_hours = set(
        df_result["data_timestamp"]
    ) if not df_result.empty else set()

    missing_reports = [
        hour for hour in required_hours
        if hour not in available_hours
    ]

    print("\nPemeriksaan enam jam selesai.")
    print("Jumlah jam yang dibutuhkan :", len(required_hours))
    print("Jumlah laporan tersedia   :", len(df_result))
    print("Jumlah jam tanpa laporan  :", len(missing_reports))

    return df_result
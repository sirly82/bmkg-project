import sqlite3
import pandas as pd

from pathlib import Path

# ============================================================
# KONFIGURASI DATABASE
# ============================================================
BASE_DIR = Path(__file__).resolve().parents[1]
DB_DIR = BASE_DIR / "data"
DB_PATH = DB_DIR / "weather.db"

TABLE_NAME = "weather_observations"

# ============================================================
# STRUKTUR TABEL
# ============================================================
CREATE_TABLE_SQL = f"""
CREATE TABLE IF NOT EXISTS {TABLE_NAME} (
    data_timestamp TEXT PRIMARY KEY,
    station_name TEXT,
    wind_dir_deg_dd INTEGER,
    wind_speed_ff INTEGER,
    pressure_qfe_mb_derived REAL,
    pressure_qff_mb_derived REAL,
    temp_drybulb_c_tttttt REAL,
    temp_dewpoint_c_tdtdtd REAL,
    relative_humidity_pc INTEGER,
    cloud_low_cover_1 INTEGER,
    cloud_cover_oktas_m INTEGER,
    rainfall_24h_rrrr REAL,
    rainfall_mm REAL,
    rainfall_period_h INTEGER,
    ix_flag TEXT,
    phenomenon TEXT,
    weather_code_ww TEXT,
    visibility_vv REAL,
    report_type TEXT,
    raw_synop TEXT
)
"""

CREATE_CACHE_SQL = """
CREATE TABLE IF NOT EXISTS synop_hour_cache (
    data_timestamp TEXT PRIMARY KEY,
    checked_at TEXT NOT NULL
)
"""

COLUMNS = [
    "data_timestamp",
    "station_name",
    "wind_dir_deg_dd",
    "wind_speed_ff",
    "pressure_qfe_mb_derived",
    "pressure_qff_mb_derived",
    "temp_drybulb_c_tttttt",
    "temp_dewpoint_c_tdtdtd",
    "relative_humidity_pc",
    "cloud_low_cover_1",
    "cloud_cover_oktas_m",
    "rainfall_24h_rrrr",
    "rainfall_mm",
    "rainfall_period_h",
    "ix_flag",
    "phenomenon",
    "weather_code_ww",
    "visibility_vv",
    "report_type",
    "raw_synop",
]

# ============================================================
# KONEKSI DAN INISIALISASI DATABASE
# ============================================================
def get_connection():
    DB_DIR.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")

    return conn

def init_db():
    with get_connection() as conn:
        conn.execute(CREATE_TABLE_SQL)
        conn.execute(CREATE_CACHE_SQL)

# ============================================================
# MENYIMPAN DATA
# ============================================================
def save_reports(df):
    """
    Menyimpan laporan SYNOP ke SQLite.

    Jika timestamp sudah ada, data lama akan diperbarui.
    """
    if df is None or df.empty:
        return 0

    missing_columns = [
        col for col in COLUMNS if col not in df.columns
    ]

    if missing_columns:
        raise ValueError(
            f"Kolom DataFrame tidak lengkap: {missing_columns}"
        )

    data = df[COLUMNS].copy()

    # Format timestamp menjadi teks untuk SQLite.
    data["data_timestamp"] = pd.to_datetime(
        data["data_timestamp"]
    ).dt.strftime("%Y-%m-%d %H:%M:%S")

    # Mengubah NaN, NaT, dan pd.NA menjadi None.
    data = data.astype(object).where(
        pd.notna(data),
        None
    )

    # Mengubah nilai NumPy menjadi tipe Python biasa.
    records = []

    for row in data.itertuples(index=False, name=None):
        cleaned_row = []

        for value in row:
            if hasattr(value, "item"):
                value = value.item()

            cleaned_row.append(value)

        records.append(tuple(cleaned_row))

    placeholders = ", ".join(["?"] * len(COLUMNS))
    column_names = ", ".join(COLUMNS)

    update_columns = [
        col for col in COLUMNS
        if col != "data_timestamp"
    ]

    update_clause = ", ".join(
        f"{col} = excluded.{col}"
        for col in update_columns
    )

    insert_sql = f"""
        INSERT INTO {TABLE_NAME} ({column_names})
        VALUES ({placeholders})
        ON CONFLICT(data_timestamp)
        DO UPDATE SET {update_clause}
    """

    with get_connection() as conn:
        before = conn.total_changes

        conn.executemany(insert_sql, records)

        saved_count = conn.total_changes - before

    return saved_count

# ============================================================
# MENGAMBIL DATA BERDASARKAN RENTANG WAKTU
# ============================================================
def get_reports(start_datetime, end_datetime):
    """
    Mengambil data dari SQLite berdasarkan rentang timestamp UTC.

    Timestamp awal dan akhir bersifat inklusif.
    """
    start = pd.Timestamp(start_datetime)
    end = pd.Timestamp(end_datetime)

    if start.tzinfo is not None:
        start = start.tz_convert("UTC").tz_localize(None)

    if end.tzinfo is not None:
        end = end.tz_convert("UTC").tz_localize(None)

    start = start.strftime("%Y-%m-%d %H:%M:%S")
    end = end.strftime("%Y-%m-%d %H:%M:%S")

    query = f"""
        SELECT {", ".join(COLUMNS)}
        FROM {TABLE_NAME}
        WHERE data_timestamp >= ?
          AND data_timestamp <= ?
        ORDER BY data_timestamp ASC
    """

    with get_connection() as conn:
        df = pd.read_sql_query(
            query,
            conn,
            params=(start, end)
        )

    if not df.empty:
        df["data_timestamp"] = pd.to_datetime(
            df["data_timestamp"]
        )

    return df

# ============================================================
# HELPER RENTANG 24 JAM (WAKTU LOKAL KE UTC)
# ============================================================
def get_utc_window_24h(target_datetime, hours_back=24, local_tz="Asia/Jakarta"):
    """
    Mengonversi waktu target lokal (default WIB) menjadi rentang (start_utc, end_utc)
    sepanjang hours_back ke belakang.
    """
    end_local = pd.Timestamp(target_datetime)
    if end_local.tzinfo is None:
        end_local = end_local.tz_localize(local_tz)

    end_utc = end_local.tz_convert("UTC").tz_localize(None)
    start_utc = end_utc - pd.Timedelta(hours=hours_back)
    return start_utc, end_utc


def get_reports_last_24h(target_datetime, hours_back=24, local_tz="Asia/Jakarta"):
    """
    Mengambil data dari SQLite untuk 24 jam ke belakang dari waktu lokal target.
    """
    start_utc, end_utc = get_utc_window_24h(
        target_datetime,
        hours_back=hours_back,
        local_tz=local_tz,
    )
    df = get_reports(start_utc, end_utc)

    if not df.empty:
        df["timestamp_local"] = (
            df["data_timestamp"]
            .dt.tz_localize("UTC")
            .dt.tz_convert(local_tz)
            .dt.tz_localize(None)
        )

    return df


# ============================================================
# MEMERIKSA TIMESTAMP YANG SUDAH TERSIMPAN & CACHE JAM
# ============================================================
def get_cached_timestamps(start_datetime, end_datetime):
    df = get_reports(start_datetime, end_datetime)

    if df.empty:
        return set()

    return set(df["data_timestamp"])


def count_reports():
    with get_connection() as conn:
        result = conn.execute(
            f"SELECT COUNT(*) FROM {TABLE_NAME}"
        ).fetchone()

    return result[0]

def get_checked_hours(start_datetime, end_datetime):
    """
    Mengambil daftar jam yang sebelumnya sudah diperiksa ke Ogimet.
    """
    start = pd.Timestamp(start_datetime)
    end = pd.Timestamp(end_datetime)

    if start.tzinfo is not None:
        start = start.tz_convert("UTC").tz_localize(None)

    if end.tzinfo is not None:
        end = end.tz_convert("UTC").tz_localize(None)

    start = start.strftime("%Y-%m-%d %H:%M:%S")
    end = end.strftime("%Y-%m-%d %H:%M:%S")

    query = """
        SELECT data_timestamp
        FROM synop_hour_cache
        WHERE data_timestamp >= ?
          AND data_timestamp <= ?
    """

    with get_connection() as conn:
        rows = conn.execute(
            query,
            (start, end)
        ).fetchall()

    return {
        pd.Timestamp(row[0])
        for row in rows
    }

def mark_hours_checked(timestamps):
    """
    Menandai jam-jam yang sudah berhasil diperiksa ke Ogimet.
    """
    now = pd.Timestamp.now(tz="UTC").tz_localize(None)
    checked_at = now.strftime("%Y-%m-%d %H:%M:%S")

    records = []

    for timestamp in timestamps:
        timestamp = pd.Timestamp(timestamp)

        if timestamp.tzinfo is not None:
            timestamp = timestamp.tz_convert(
                "UTC"
            ).tz_localize(None)

        records.append((
            timestamp.strftime("%Y-%m-%d %H:%M:%S"),
            checked_at
        ))

    if not records:
        return

    query = """
        INSERT INTO synop_hour_cache (
            data_timestamp,
            checked_at
        )
        VALUES (?, ?)
        ON CONFLICT(data_timestamp)
        DO UPDATE SET checked_at = excluded.checked_at
    """

    with get_connection() as conn:
        conn.executemany(query, records)

def get_recent_observations(limit=25):
    """
    Mengambil N data observasi terbaru dari SQLite untuk pratinjau database.
    """
    query = f"""
        SELECT {", ".join(COLUMNS)}
        FROM {TABLE_NAME}
        ORDER BY rowid DESC
        LIMIT ?
    """
    with get_connection() as conn:
        df = pd.read_sql_query(query, conn, params=(limit,))

    return df
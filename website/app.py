import sys
from pathlib import Path

WEBSITE_DIR = Path(__file__).resolve().parent
if str(WEBSITE_DIR) not in sys.path:
    sys.path.insert(0, str(WEBSITE_DIR))

import streamlit as st

from datetime import datetime, time
from zoneinfo import ZoneInfo

from components.data_handler import fetch_and_predict
from components.display_handler import display_results
from components.style import apply_custom_style
from modules.database import DB_PATH, count_reports, get_recent_observations

# ============================================================
# 1. KONFIGURASI HALAMAN
# ============================================================
st.set_page_config(
    page_title="Weather Monitoring - BMKG Jambi",
    page_icon="🌦️",
    layout="wide"
)

apply_custom_style()

# ============================================================
# 2. KONFIGURASI WAKTU
# ============================================================
TIMEZONES = {
    "WIB — Asia/Jakarta (UTC+7)": "Asia/Jakarta",
    "WITA — Asia/Makassar (UTC+8)": "Asia/Makassar",
    "WIT — Asia/Jayapura (UTC+9)": "Asia/Jayapura",
    "UTC — Coordinated Universal Time": "UTC",
    "Singapore — Asia/Singapore": "Asia/Singapore",
    "Tokyo — Asia/Tokyo": "Asia/Tokyo",
    "London — Europe/London": "Europe/London",
    "New York — America/New_York": "America/New_York",
}

# ============================================================
# 3. HEADER
# (st.title dihapus karena judulnya sudah ada di banner di bawah,
#  sebelumnya judul tampil dobel)
# ============================================================
st.markdown(
    """
    <div class="main-header">
        <h1>🌦️ Weather Monitoring</h1>
        <p>
            Sistem Monitoring dan Klasifikasi Fenomena Cuaca
            berdasarkan data observasi SYNOP
            Stasiun Meteorologi Sultan Thaha Jambi.
        </p>
        <div class="chips">
            <span class="chip">Data SYNOP</span>
            <span class="chip">Riwayat 24 jam</span>
            <span class="chip">LightGBM</span>
        </div>
    </div>
    """,
    unsafe_allow_html=True
)

# ============================================================
# 4. INPUT TANGGAL DAN WAKTU (preview langsung berubah)
# ============================================================
with st.container(border=True, key="time_settings"):
    st.subheader("🕒 Pengaturan Waktu Observasi")
    st.caption("Tentukan tanggal, jam, dan zona waktu pengamatan.")

    selected_timezone_label = st.selectbox(
        "Zona waktu",
        options=list(TIMEZONES.keys()),
        index=0,
        key="timezone_label"
    )
    selected_tz = ZoneInfo(TIMEZONES[selected_timezone_label])
    now = datetime.now(selected_tz)

    use_now = st.checkbox("Gunakan jam sekarang", key="use_now")

    # Rapikan nilai tersimpan supaya tidak melewati batas
    today = now.date()
    if "manual_date" not in st.session_state or st.session_state["manual_date"] > today:
        st.session_state["manual_date"] = today

    col_date, col_time = st.columns(2)
    with col_date:
        selected_date = st.date_input(
            "Tanggal observasi",
            max_value=today,
            key="manual_date",
            disabled=use_now
        )

    # Jam yang boleh dipilih: sampai jam sekarang jika tanggalnya hari ini.
    max_hour = now.hour if selected_date == today else 23
    hour_options = list(range(max_hour + 1))

    if "manual_hour" not in st.session_state or st.session_state["manual_hour"] not in hour_options:
        st.session_state["manual_hour"] = max_hour

    with col_time:
        selected_hour = st.selectbox(
            "Jam observasi",
            options=hour_options,
            format_func=lambda x: f"{x:02d}:00",
            key="manual_hour",
            disabled=use_now
        )

    # Waktu dihitung langsung dari input saat ini, tanpa tombol perantara.
    if use_now:
        candidate_datetime = now.replace(minute=0, second=0, microsecond=0)
    else:
        candidate_datetime = datetime.combine(
            selected_date,
            time(selected_hour, 0)
        ).replace(tzinfo=selected_tz)

    is_future = candidate_datetime > now

    st.markdown("#### Waktu observasi terpilih")
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Tanggal", candidate_datetime.strftime("%d-%m-%Y"))
    with col2:
        st.metric("Jam", candidate_datetime.strftime("%H:%M"))
    st.caption(f"Zona waktu: {selected_timezone_label}")

    if is_future:
        st.error("Waktu observasi tidak boleh melebihi waktu saat ini.")

selected_datetime = None if is_future else candidate_datetime

# ============================================================
# 5. TOMBOL PENGAMBILAN DATA DAN PREDIKSI
# ============================================================
st.write("")

force_refresh = st.checkbox(
    "Paksa ambil ulang data terbaru dari Ogimet (abaikan cache)",
    value=False,
    key="force_refresh",
)

load_data = st.button(
    "🌦️ Tampilkan Data dan Hasil",
    type="primary",
    disabled=selected_datetime is None,
    width="stretch"
)

if load_data and selected_datetime is not None:
    # Hapus hasil sebelumnya agar tidak tertukar jika pencarian baru gagal.
    st.session_state.pop("weather_df", None)

    try:
        with st.spinner("Mengambil data 24 jam dan menjalankan prediksi..."):
            result_df = fetch_and_predict(
                selected_datetime=selected_datetime,
                selected_timezone=TIMEZONES[selected_timezone_label],
                force_refresh=force_refresh,
            )

        st.session_state["weather_df"] = result_df
        st.session_state["result_selected_datetime"] = selected_datetime.isoformat()
        st.session_state["result_timezone_label"] = selected_timezone_label

        st.success("Pengambilan data dan proses prediksi selesai.")
    except Exception as error:
        st.error(f"Terjadi kesalahan saat memproses data: {error}")

# ============================================================
# 6. TAMPILAN HASIL
# ============================================================
st.divider()

if "weather_df" in st.session_state:
    display_results(
        df=st.session_state["weather_df"],
        selected_datetime_iso=st.session_state["result_selected_datetime"],
        selected_timezone_label=st.session_state["result_timezone_label"],
        timezones=TIMEZONES
    )
else:
    st.info(
        "Hasil belum tersedia. Pilih tanggal dan jam, "
        "lalu klik Tampilkan Data dan Hasil."
    )

with st.expander("🗄️ Inspeksi Database Lokal (SQLite)"):
    if DB_PATH.exists():
        total_rows = count_reports()
        st.caption(
            f"Lokasi file: `{DB_PATH.name}` | "
            f"Total data tersimpan: **{total_rows} baris**"
        )

        recent_df = get_recent_observations(limit=25)
        if not recent_df.empty:
            st.dataframe(
                recent_df,
                width="stretch",
                hide_index=True,
                height=300,
            )
        else:
            st.info("Tabel observasi masih kosong.")

        st.download_button(
            label="⬇️ Unduh File Database (weather.db)",
            data=DB_PATH.read_bytes(),
            file_name="weather.db",
            mime="application/octet-stream",
        )
    else:
        st.info("File database belum terbentuk. Lakukan pengambilan data terlebih dahulu.")

# ============================================================
# 7. FOOTER
# ============================================================
st.divider()
st.markdown(
    """
    <div class="custom-footer">
        Prototype Monitoring dan Klasifikasi Fenomena Cuaca
        <br>
        Stasiun Meteorologi Kelas I Sultan Thaha Jambi
    </div>
    """,
    unsafe_allow_html=True
)
import streamlit as st
from datetime import datetime, time
from zoneinfo import ZoneInfo

from components.data_handler import fetch_and_predict
from components.display_handler import display_results
from components.style import apply_custom_style

# ============================================================
# 1. KONFIGURASI HALAMAN
# ============================================================
st.set_page_config(
    page_title="Visibility Monitoring - BMKG Jambi",
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
        <h1>🌦️ Visibility Monitoring</h1>
        <p>
            Sistem monitoring dan klasifikasi fenomena visibility
            berdasarkan data observasi SYNOP
            Stasiun Meteorologi Sultan Thaha Jambi.
        </p>
        <div class="chips">
            <span class="chip">Data SYNOP</span>
            <span class="chip">Riwayat 24 jam</span>
            <span class="chip">Decision Tree</span>
        </div>
    </div>
    """,
    unsafe_allow_html=True
)

# ============================================================
# 4. INPUT TANGGAL DAN WAKTU
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

    time_method = st.radio(
        "Cara menentukan waktu",
        ["Waktu sekarang", "Pilih manual"],
        horizontal=True
    )
    now = datetime.now(selected_tz)

    if time_method == "Waktu sekarang":
        st.caption(
            f"Sekarang: {now.strftime('%d-%m-%Y %H:%M')} "
            "(dibulatkan ke jam penuh)"
        )
        if st.button("Gunakan jam sekarang", width="stretch"):
            st.session_state["selected_datetime"] = now.replace(
                minute=0,
                second=0,
                microsecond=0
            ).isoformat()
    else:
        col_date, col_time = st.columns(2)

        with col_date:
            selected_date = st.date_input(
                "Tanggal observasi",
                value=now.date(),
                max_value=now.date(),
                key="manual_date"
            )
        with col_time:
            selected_hour = st.selectbox(
                "Jam observasi",
                options=list(range(24)),
                index=now.hour,
                format_func=lambda x: f"{x:02d}:00",
                key="manual_hour"
            )

        if st.button("Gunakan waktu ini", width="stretch"):
            candidate_datetime = datetime.combine(
                selected_date,
                time(selected_hour, 0)
            ).replace(tzinfo=selected_tz)

            if candidate_datetime > now:
                st.error("Waktu observasi tidak boleh melebihi waktu saat ini.")
            else:
                st.session_state["selected_datetime"] = candidate_datetime.isoformat()

    # Ambil waktu yang telah disimpan.
    selected_datetime = None
    if st.session_state.get("selected_datetime"):
        selected_datetime = datetime.fromisoformat(
            st.session_state["selected_datetime"]
        ).astimezone(selected_tz)

        st.markdown("#### Waktu observasi terpilih")
        col1, col2 = st.columns(2)

        with col1:
            st.metric("Tanggal", selected_datetime.strftime("%d-%m-%Y"))
        with col2:
            st.metric("Jam", selected_datetime.strftime("%H:%M"))

        st.caption(f"Zona waktu: {selected_timezone_label}")
    else:
        st.info("Tentukan waktu observasi terlebih dahulu.")

# ============================================================
# 5. TOMBOL PENGAMBILAN DATA DAN PREDIKSI
# ============================================================
st.write("")  # jarak antar kartu dan tombol
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
                selected_timezone=TIMEZONES[selected_timezone_label]
            )

        # Simpan hasil agar tetap tersedia saat Streamlit rerun.
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

# ============================================================
# 7. FOOTER
# ============================================================
st.divider()
st.markdown(
    """
    <div class="custom-footer">
        Prototype Monitoring dan Klasifikasi Fenomena Visibility
        <br>
        Stasiun Meteorologi Kelas I Sultan Thaha Jambi
    </div>
    """,
    unsafe_allow_html=True
)
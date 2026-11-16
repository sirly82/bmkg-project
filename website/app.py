import streamlit as st
from datetime import datetime, time
from zoneinfo import ZoneInfo

from components.data_handler import fetch_and_predict
from components.display_handler import display_results

# ============================================================
# 1. KONFIGURASI HALAMAN
# ============================================================
st.set_page_config(
    page_title="Visibility Monitoring - BMKG Jambi",
    page_icon="🌦️",
    layout="wide"
)

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
# ============================================================
st.title("🌦️ Visibility Monitoring")
st.caption(
    "Monitoring dan klasifikasi fenomena visibility "
    "berdasarkan data observasi SYNOP Stasiun Meteorologi "
    "Sultan Thaha Jambi."
)
st.divider()

# ============================================================
# 4. INPUT TANGGAL DAN WAKTU
# ============================================================
st.subheader("Pengaturan Waktu Observasi")

selected_timezone_label = st.selectbox(
    "Pilih Zona Waktu",
    options=list(TIMEZONES.keys()),
    index=0,
    key="timezone_label"
)
selected_tz = ZoneInfo(TIMEZONES[selected_timezone_label])

time_method = st.radio(
    "Pilih Cara Menentukan Waktu",
    ["Lihat Jam Sekarang", "Pilih Waktu Manual"],
    horizontal=True
)

now = datetime.now(selected_tz)

if time_method == "Lihat Jam Sekarang":
    if st.button("🕒 Lihat Jam Sekarang", width="stretch"):
        selected_datetime = now.replace(
            minute=0,
            second=0,
            microsecond=0
        )
        st.session_state["selected_datetime"] = selected_datetime.isoformat()
elif time_method == "Pilih Waktu Manual":
    col_date, col_time = st.columns(2)

    with col_date:
        selected_date = st.date_input(
            "Tanggal Observasi",
            value=now.date(),
            max_value=now.date(),
            key="manual_date"
        )
    with col_time:
        selected_hour = st.selectbox(
            "Jam Observasi",
            options=list(range(24)),
            index=now.hour,
            format_func=lambda x: f"{x:02d}:00",
            key="manual_hour"
        )

    if st.button("Gunakan Waktu Ini", width="stretch"):
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

    st.markdown("### Preview Waktu Observasi")
    col1, col2 = st.columns(2)

    with col1:
        st.metric("Tanggal", selected_datetime.strftime("%d-%m-%Y"))
    with col2:
        st.metric("Jam", selected_datetime.strftime("%H:%M"))

    st.caption(f"Zona waktu: {selected_timezone_label}")
else:
    st.info("Silakan tentukan waktu observasi terlebih dahulu.")

# ============================================================
# 5. TOMBOL PENGAMBILAN DATA DAN PREDIKSI
# ============================================================
load_data = st.button(
    "Tampilkan Data dan Prediksi",
    type="primary",
    disabled=selected_datetime is None,
    width="stretch"
)

if load_data and selected_datetime is not None:
    # Hapus hasil pencarian sebelumnya agar tidak tertukar jika pencarian baru gagal.
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
if "weather_df" in st.session_state:
    display_results(
        df=st.session_state["weather_df"],
        selected_datetime_iso=st.session_state["result_selected_datetime"],
        selected_timezone_label=selected_timezone_label,
        timezones=TIMEZONES
    )
else:
    st.info(
        "Hasil belum tersedia. Pilih tanggal dan jam, "
        "kemudian klik Tampilkan Data dan Prediksi."
    )

# ============================================================
# 7. FOOTER
# ============================================================
st.divider()
st.caption(
    "Prototype Monitoring dan Klasifikasi Fenomena Visibility "
    "| Stasiun Meteorologi Kelas I Sultan Thaha Jambi"
)
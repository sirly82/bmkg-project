import streamlit as st
import pandas as pd

from datetime import date, time, datetime, timezone
from zoneinfo import ZoneInfo

from weather_service import get_six_hour_data
from model_utils import predict_phenomenon

# ============================================================
# 1. KONFIGURASI HALAMAN
# ============================================================
st.set_page_config(
    page_title="Visibility Monitoring - BMKG Jambi",
    page_icon="🌦️",
    layout="wide"
)

def reset_selected_time():
    st.session_state.pop("selected_datetime", None)

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
# 4. PEMILIHAN TANGGAL DAN WAKTU
# ============================================================
st.subheader("Pengaturan Waktu Observasi")

selected_timezone_label = st.selectbox(
    "Pilih Zona Waktu",
    options=list(TIMEZONES.keys()),
    index=0,
    key="timezone_label"
)
selected_tz = ZoneInfo(TIMEZONES[selected_timezone_label])

# Pilihan cara menentukan waktu
time_method = st.radio(
    "Pilih Cara Menentukan Waktu",
    ["Lihat Jam Sekarang", "Pilih Waktu Manual"],
    horizontal=True
)
selected_datetime = None

if time_method == "Lihat Jam Sekarang":
    if st.button("🕒 Lihat Jam Sekarang", width="stretch"):
        now = datetime.now(selected_tz)

        selected_datetime = now.replace(
            minute=0,
            second=0,
            microsecond=0
        )
        st.session_state["selected_datetime"] = (
            selected_datetime.isoformat()
        )
elif time_method == "Pilih Waktu Manual":
    now = datetime.now(selected_tz)

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
        selected_time = time(selected_hour, 0)

    if st.button("Gunakan Waktu Ini", width="stretch"):
        selected_datetime = datetime.combine(
            selected_date,
            selected_time
        ).replace(tzinfo=selected_tz)

        if selected_datetime > now:
            st.error(
                "Waktu observasi tidak boleh melebihi "
                "waktu saat ini."
            )
        else:
            st.session_state["selected_datetime"] = (
                selected_datetime.isoformat()
            )

# Ambil waktu yang sudah dipilih dari session state
if "selected_datetime" in st.session_state:
    selected_datetime = datetime.fromisoformat(
        st.session_state["selected_datetime"]
    )

    # Konversi ke zona waktu yang sedang dipilih
    selected_datetime = selected_datetime.astimezone(selected_tz)

    st.markdown("### Preview Waktu Observasi")

    col1, col2 = st.columns(2)

    with col1:
        st.metric(
            "Tanggal",
            selected_datetime.strftime("%d-%m-%Y")
        )
    with col2:
        st.metric(
            "Jam",
            selected_datetime.strftime("%H:%M")
        )
    st.caption(f"Zona waktu: {selected_timezone_label}")
else:
    st.info("Silakan tentukan waktu observasi terlebih dahulu.")

load_data = st.button(
    "Tampilkan Data dan Prediksi",
    type="primary",
    disabled="selected_datetime" not in st.session_state,
    width="stretch"
)

# ============================================================
# 5. FUNGSI BANTUAN
# ============================================================
def format_value(value, suffix=""):
    """Mengubah nilai menjadi teks yang mudah dibaca."""

    if pd.isna(value):
        return "-"

    return f"{value}{suffix}"

def get_observed_phenomenon(row):
    """
    Mengambil fenomena aktual berdasarkan kode WW.
    Jika WW tidak tersedia, hasilnya tidak dianggap Normal.
    """

    ix_flag = row["ix_flag"]
    weather_code_ww = row["weather_code_ww"]

    # Tidak ada fenomena signifikan
    if pd.notna(ix_flag) and int(ix_flag) in [2, 5]:
        return "Tidak ada Fenomena Signifikan"

    # Pengamatan tidak dilakukan atau data tidak tersedia
    if pd.notna(ix_flag) and int(ix_flag) in [3, 6]:
        return "Tidak tersedia"

    if pd.notna(weather_code_ww):
        return row["phenomenon"]

    return "Tidak tersedia"

def compare_prediction(predicted, observed):
    if observed == "Tidak ada Fenomena Signifikan":
        return "Sesuai" if predicted == "Normal" else "Berbeda"

    if observed == "Tidak tersedia":
        return "Tidak dapat dibandingkan"

    return "Sesuai" if predicted == observed else "Berbeda"

if load_data:
    try:
        # ============================================================
        # 6. PROSES PENGAMBILAN DATA DAN PREDIKSI
        # ============================================================
        # Mengambil data observasi
        try:
            with st.spinner("Mengambil data observasi..."):
                # Mengambil enam jam data
                df = get_six_hour_data(selected_datetime)

                print("\n=== PEMERIKSAAN LAPORAN SYNOP ===")
                print(
                    df[
                        [
                            "data_timestamp",
                            "ix_flag",
                            "weather_code_ww",
                            "phenomenon",
                            "raw_synop"
                        ]
                    ].to_string(index=False)
                )
                print("================================")
        except Exception as error:
            st.error(
                f"Gagal mengambil data observasi: {error}"
            )
            st.stop()

        # Memeriksa apakah data tersedia
        if df is None or df.empty:
            st.warning(
                "Data observasi tidak ditemukan untuk "
                "tanggal dan jam yang dipilih."
            )
            st.info(
                "Silakan pilih waktu pengamatan lainnya."
            )
            st.stop()

        # Jika data tersedia, lanjutkan proses prediksi
        try:
            with st.spinner("Menjalankan prediksi model..."):
                # Mengurutkan data berdasarkan waktu
                df = df.copy()

                df["data_timestamp"] = pd.to_datetime(
                    df["data_timestamp"],
                    utc=True
                )
                df = df.sort_values(
                    "data_timestamp"
                ).reset_index(drop=True)

                # Menyiapkan hasil prediksi
                prediction_results = []

                for _, row in df.iterrows():
                    try:
                        result = predict_phenomenon(row)

                        prediction_results.append({
                            "predicted_class":
                                result["predicted_class"],
                            "confidence":
                                result["confidence"],
                            "probabilities":
                                result["probabilities"],
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
        except Exception as error:
            st.error(
                f"Terjadi kesalahan saat prediksi: {error}"
            )
            st.stop()
        st.success(
            "Pengambilan data dan proses prediksi selesai."
        )

        # ====================================================
        # 7. MENENTUKAN DATA PADA JAM YANG DIPILIH
        # ====================================================
        selected_datetime = datetime.fromisoformat(
            st.session_state["selected_datetime"]
        )
        selected_utc = selected_datetime.astimezone(timezone.utc)

        df["data_timestamp"] = pd.to_datetime(
            df["data_timestamp"],
            utc=True
        )
        selected_row = df[
            df["data_timestamp"] == pd.Timestamp(selected_utc)
        ]

        if selected_row.empty:
            st.warning(
                "Laporan observasi pada jam yang dipilih "
                "tidak ditemukan. Data enam jam tetap dapat "
                "ditampilkan jika tersedia."
            )
            selected_data = None
        else:
            selected_data = selected_row.iloc[0]

        # ====================================================
        # 8. HASIL PREDIKSI UTAMA
        # ====================================================
        st.divider()
        st.subheader("Hasil Prediksi")

        if selected_data is not None:
            result = selected_data["prediction_result"]

            if result["error"] is not None:
                st.error(
                    "Prediksi tidak dapat dilakukan: "
                    + result["error"]
                )
            else:
                predicted_class = result["predicted_class"]
                confidence = result["confidence"]

                col1, col2 = st.columns(2)

                with col1:
                    st.metric(
                        "Fenomena Prediksi",
                        predicted_class
                    )
                    st.metric(
                        "Confidence",
                        f"{confidence:.2%}"
                    )
                with col2:
                    observed = get_observed_phenomenon(
                        selected_data
                    )
                    st.metric(
                        "Fenomena Aktual (WW)",
                        observed
                    )

                    if observed == "Tidak tersedia":
                        st.info(
                            "Informasi fenomena aktual tidak tersedia "
                            "pada laporan observasi ini."
                        )
                    else:
                        comparison = compare_prediction(
                            predicted_class,
                            observed
                        )
                        if comparison == "Sesuai":
                            st.success(
                                "Prediksi sesuai dengan "
                                "fenomena aktual."
                            )
                        else:
                            st.warning(
                                "Prediksi berbeda dengan "
                                "fenomena aktual."
                            )

                # =================================================
                # 9. PROBABILITAS SETIAP KELAS
                # =================================================
                st.subheader("Probabilitas Setiap Kelas")
                probability_df = pd.DataFrame({
                    "Fenomena": list(
                        result["probabilities"].keys()
                    ),
                    "Probabilitas": list(
                        result["probabilities"].values()
                    )
                })
                probability_df = probability_df.set_index(
                    "Fenomena"
                )
                st.bar_chart(
                    probability_df,
                    x_label="Fenomena",
                    y_label="Probabilitas",
                    horizontal=True
                )

                # =================================================
                # 10. PARAMETER METEOROLOGI
                # =================================================
                st.divider()

                st.subheader(
                    "Parameter Meteorologi"
                )

                col1, col2, col3 = st.columns(3)

                with col1:
                    st.metric(
                        "Visibility (VV)",
                        format_value(
                            selected_data["visibility_vv"]
                        )
                    )
                    st.metric(
                        "Suhu Udara",
                        format_value(
                            selected_data[
                                "temp_drybulb_c_tttttt"
                            ],
                            " °C"
                        )
                    )
                    st.metric(
                        "Titik Embun",
                        format_value(
                            selected_data[
                                "temp_dewpoint_c_tdtdtd"
                            ],
                            " °C"
                        )
                    )
                with col2:
                    st.metric(
                        "Kelembapan Relatif",
                        format_value(
                            selected_data[
                                "relative_humidity_pc"
                            ],
                            " %"
                        )
                    )
                    st.metric(
                        "Tekanan QFF",
                        format_value(
                            selected_data[
                                "pressure_qff_mb_derived"
                            ],
                            " hPa"
                        )
                    )
                    st.metric(
                        "Kecepatan Angin",
                        format_value(
                            selected_data["wind_speed_ff"]
                        )
                    )
                with col3:
                    st.metric(
                        "Arah Angin",
                        format_value(
                            selected_data["wind_dir_deg_dd"],
                            "°"
                        )
                    )
                    st.metric(
                        "Tutupan Awan Rendah",
                        format_value(
                            selected_data["cloud_low_cover_1"]
                        )
                    )
                    st.metric(
                        "Tutupan Awan",
                        format_value(
                            selected_data["cloud_cover_oktas_m"]
                        )
                    )

        # ====================================================
        # 11. TIMELINE ENAM JAM
        # ====================================================
        st.divider()
        st.subheader("Timeline Fenomena Enam Jam")

        timeline_rows = []

        for _, row in df.iterrows():
            timestamp_local = row["data_timestamp"].tz_convert(selected_tz)
            result = row["prediction_result"]

            if result["error"] is None:
                predicted = result["predicted_class"]
            else:
                predicted = "Prediksi tidak tersedia"

            observed = get_observed_phenomenon(row)

            if predicted == "Prediksi tidak tersedia":
                comparison = "Tidak dapat dibandingkan"
            else:
                comparison = compare_prediction(
                    predicted,
                    observed
                )

            timeline_rows.append({
                "Waktu WIB": timestamp_local.strftime(
                    "%d-%m-%Y %H:%M"
                ),
                "Prediksi Model": predicted,
                "Fenomena Aktual (WW)": observed,
                "Perbandingan": comparison
            })

        timeline_df = pd.DataFrame(timeline_rows)

        st.dataframe(
            timeline_df,
            use_container_width=True,
            hide_index=True
        )

        # ====================================================
        # 12. GRAFIK VISIBILITY
        # ====================================================
        st.divider()
        st.subheader("Grafik Visibility")

        visibility_df = df[["data_timestamp", "visibility_vv"]].copy()
        visibility_df["Waktu"] = (
            visibility_df["data_timestamp"]
            .dt.tz_convert(selected_tz)
            .dt.strftime("%H:%M")
        )
        visibility_df = visibility_df.set_index("Waktu")
        st.line_chart(
            visibility_df,
            y="visibility_vv",
            y_label="Nilai visibility (VV)"
        )
        st.caption(
            "Grafik menampilkan nilai VV hasil decoding "
            "SYNOP, bukan otomatis jarak dalam meter."
        )
    except Exception as error:
        st.error(
            f"Terjadi kesalahan saat memproses data: {error}"
        )
else:
    st.info(
        "Silakan pilih tanggal dan jam, "
        "kemudian klik Tampilkan Data dan Prediksi."
    )

# ============================================================
# 13. FOOTER
# ============================================================
st.divider()

st.caption(
    "Prototype Monitoring dan Klasifikasi Fenomena Visibility "
    "| Stasiun Meteorologi Kelas I Sultan Thaha Jambi"
)
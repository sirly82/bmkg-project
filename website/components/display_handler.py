from datetime import datetime, timezone
from zoneinfo import ZoneInfo

import pandas as pd
import streamlit as st

def format_value(value, suffix=""):
    """Mengubah nilai menjadi teks yang mudah dibaca."""
    if pd.isna(value):
        return "-"
    return f"{value}{suffix}"

def get_observed_phenomenon(row):
    """
    Mengambil fenomena aktual berdasarkan kode WW dan ix_flag.
    Ketiadaan kode WW tidak otomatis dianggap sebagai Normal.
    """
    ix_flag = row.get("ix_flag")
    weather_code_ww = row.get("weather_code_ww")

    if pd.notna(ix_flag):
        try:
            ix_flag = int(ix_flag)
        except (TypeError, ValueError):
            ix_flag = None

    # Tidak ada fenomena signifikan.
    if ix_flag in [2, 5]:
        return "Tidak ada Fenomena Signifikan"

    # Pengamatan tidak dilakukan atau data tidak tersedia.
    if ix_flag in [3, 6]:
        return "Tidak tersedia"

    if pd.notna(weather_code_ww):
        phenomenon = row.get("phenomenon")
        if pd.notna(phenomenon):
            return phenomenon

    # Pertahankan hasil decoding dari scraper bila tersedia.
    phenomenon = row.get("phenomenon")
    if pd.notna(phenomenon):
        return phenomenon

    return "Tidak tersedia"

def compare_prediction(predicted, observed):
    if observed == "Tidak ada Fenomena Signifikan":
        return "Sesuai" if predicted == "Normal" else "Berbeda"

    if observed == "Tidak tersedia":
        return "Tidak dapat dibandingkan"

    return "Sesuai" if predicted == observed else "Berbeda"

def _display_main_prediction(selected_data):
    st.divider()
    st.subheader("Hasil Prediksi")

    if selected_data is None:
        st.warning(
            "Laporan observasi pada jam yang dipilih tidak ditemukan. "
            "Riwayat data yang tersedia tetap dapat ditampilkan."
        )
        return

    result = selected_data["prediction_result"]

    if result["error"] is not None:
        st.error(
            "Prediksi tidak dapat dilakukan: " + result["error"]
        )
        return

    predicted_class = result["predicted_class"]
    confidence = result["confidence"]

    col1, col2 = st.columns(2)

    with col1:
        st.metric("Fenomena Prediksi", predicted_class)
        st.metric("Confidence", f"{confidence:.2%}")
    with col2:
        observed = get_observed_phenomenon(selected_data)
        st.metric("Fenomena Aktual (WW)", observed)

        if observed == "Tidak tersedia":
            st.info(
                "Informasi fenomena aktual tidak tersedia "
                "pada laporan observasi ini."
            )
        else:
            comparison = compare_prediction(predicted_class, observed)

            if comparison == "Sesuai":
                st.success("Prediksi sesuai dengan fenomena aktual.")
            else:
                st.warning("Prediksi berbeda dengan fenomena aktual.")

    st.subheader("Probabilitas Setiap Kelas")

    probabilities = result["probabilities"] or {}
    if probabilities:
        probability_df = pd.DataFrame({
            "Fenomena": list(probabilities.keys()),
            "Probabilitas": list(probabilities.values())
        }).set_index("Fenomena")

        st.bar_chart(
            probability_df,
            x_label="Fenomena",
            y_label="Probabilitas",
            horizontal=True
        )
    else:
        st.info("Informasi probabilitas tidak tersedia.")

def _display_meteorological_parameters(selected_data):
    if selected_data is None:
        return

    st.divider()
    st.subheader("Parameter Meteorologi")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric(
            "Visibility (VV)",
            format_value(selected_data.get("visibility_vv"))
        )
        st.metric(
            "Suhu Udara",
            format_value(selected_data.get("temp_drybulb_c_tttttt"), " °C")
        )
        st.metric(
            "Titik Embun",
            format_value(selected_data.get("temp_dewpoint_c_tdtdtd"), " °C")
        )
    with col2:
        st.metric(
            "Kelembapan Relatif",
            format_value(selected_data.get("relative_humidity_pc"), " %")
        )
        st.metric(
            "Tekanan QFF",
            format_value(selected_data.get("pressure_qff_mb_derived"), " hPa")
        )
        st.metric(
            "Kecepatan Angin",
            format_value(selected_data.get("wind_speed_ff"))
        )
    with col3:
        st.metric(
            "Arah Angin",
            format_value(selected_data.get("wind_dir_deg_dd"), "°")
        )
        st.metric(
            "Tutupan Awan Rendah",
            format_value(selected_data.get("cloud_low_cover_1"))
        )
        st.metric(
            "Tutupan Awan",
            format_value(selected_data.get("cloud_cover_oktas_m"))
        )

def _build_timeline(phenomenon_df, selected_tz):
    timeline_rows = []

    for _, row in phenomenon_df.iterrows():
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
            comparison = compare_prediction(predicted, observed)

        timeline_rows.append({
            "Waktu": timestamp_local.strftime("%d-%m-%Y %H:%M"),
            "Prediksi Model": predicted,
            "Fenomena Aktual (WW)": observed,
            "Perbandingan": comparison
        })

    return pd.DataFrame(timeline_rows)

def _display_timeline(df, selected_utc, selected_tz, selected_duration):
    end_time = pd.Timestamp(selected_utc)
    start_time = end_time - pd.Timedelta(hours=selected_duration - 1)

    phenomenon_df = df[
        (df["data_timestamp"] >= start_time) &
        (df["data_timestamp"] <= end_time)
    ].copy()

    phenomenon_df = (
        phenomenon_df
        .sort_values("data_timestamp")
        .reset_index(drop=True)
    )

    st.divider()
    st.subheader(
        f"Timeline Fenomena {selected_duration} Jam Terakhir"
    )

    timeline_df = _build_timeline(phenomenon_df, selected_tz)

    if timeline_df.empty:
        st.info("Tidak ada laporan pada rentang waktu yang dipilih.")
    else:
        st.dataframe(
            timeline_df,
            width="stretch",
            hide_index=True
        )

def _display_visibility_chart(df, selected_utc, selected_tz, selected_duration):
    st.divider()
    st.subheader("Grafik Visibility")

    end_time = pd.Timestamp(selected_utc)
    start_time = end_time - pd.Timedelta(hours=selected_duration - 1)

    visibility_df = df[
        (df["data_timestamp"] >= start_time) &
        (df["data_timestamp"] <= end_time)
    ][["data_timestamp", "visibility_vv"]].copy()

    visibility_df = visibility_df.sort_values("data_timestamp")

    if visibility_df.empty:
        st.info("Data visibility tidak tersedia pada rentang waktu ini.")
        return

    visibility_df["Waktu"] = (
        visibility_df["data_timestamp"]
        .dt.tz_convert(selected_tz)
        .dt.strftime("%d/%m %H:%M")
    )

    visibility_df = visibility_df.set_index("Waktu")

    st.line_chart(
        visibility_df,
        y="visibility_vv",
        y_label="Nilai visibility (VV)"
    )

    st.caption(
        "Grafik menampilkan nilai VV hasil decoding SYNOP, "
        "bukan otomatis jarak dalam meter."
    )

def display_results(
    df,
    selected_datetime_iso,
    selected_timezone_label,
    timezones
):
    """
    Menampilkan seluruh hasil berdasarkan data yang sudah tersimpan.
    Fungsi ini boleh dijalankan ulang saat widget durasi berubah;
    tidak melakukan scraping maupun prediksi.
    """
    if df is None or df.empty:
        st.warning("Data hasil pengamatan tidak tersedia.")
        return

    selected_tz = ZoneInfo(timezones[selected_timezone_label])
    selected_datetime = datetime.fromisoformat(
        selected_datetime_iso
    ).astimezone(selected_tz)
    selected_utc = selected_datetime.astimezone(timezone.utc)

    df = df.copy()
    df["data_timestamp"] = pd.to_datetime(
        df["data_timestamp"],
        utc=True
    )

    st.divider()
    st.subheader("Pengaturan Tampilan Fenomena")

    selected_duration = st.selectbox(
        "Pilih rentang waktu fenomena:",
        options=[24, 12, 6, 3],
        format_func=lambda x: f"{x} jam terakhir",
        index=2,
        key="selected_duration"
    )

    # Data pada satu jam yang dipilih user.
    selected_row = df[
        df["data_timestamp"] == pd.Timestamp(selected_utc)
    ]

    if selected_row.empty:
        selected_data = None
    else:
        selected_data = selected_row.iloc[0]

    _display_main_prediction(selected_data)
    _display_meteorological_parameters(selected_data)
    _display_timeline(
        df=df,
        selected_utc=selected_utc,
        selected_tz=selected_tz,
        selected_duration=selected_duration
    )
    _display_visibility_chart(
        df=df,
        selected_utc=selected_utc,
        selected_tz=selected_tz,
        selected_duration=selected_duration
    )
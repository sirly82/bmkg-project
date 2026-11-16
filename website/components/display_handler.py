from datetime import datetime, timezone
from zoneinfo import ZoneInfo

import pandas as pd
import streamlit as st
import altair as alt

CHART_COLOR = "#1F6F78"

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

COMPARISON_ICON = {
    "Sesuai": "✅ Sesuai",
    "Berbeda": "⚠️ Berbeda",
    "Tidak dapat dibandingkan": "➖ Tidak dapat dibandingkan",
}

def _display_main_prediction(selected_data):
    st.divider()
    st.subheader("🎯 Hasil Prediksi")

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
    observed = get_observed_phenomenon(selected_data)

    with st.container(border=True, key="prediction_summary"):
        # Kolom ketiga dibuat lebih lebar karena teks fenomena aktual panjang.
        col1, col2, col3 = st.columns([1, 1, 1.4])

        with col1:
            st.metric("🌫️ Fenomena Prediksi", predicted_class)
        with col2:
            st.metric("🎯 Tingkat Kepercayaan", f"{confidence:.2%}")
        with col3:
            st.metric("📋 Fenomena Aktual (WW)", observed)

        if observed == "Tidak tersedia":
            st.info(
                "Informasi fenomena aktual tidak tersedia "
                "pada laporan observasi ini."
            )
        else:
            comparison = compare_prediction(predicted_class, observed)

            if comparison == "Sesuai":
                st.success("Hasil klasifikasi sesuai dengan fenomena aktual.")
            elif comparison == "Tidak dapat dibandingkan":
                st.info("Hasil klasifikasi tidak dapat dibandingkan.")
            else:
                st.warning("Hasil klasifikasi berbeda dengan fenomena aktual.")

    st.subheader("📊 Probabilitas Setiap Kelas")
    probabilities = result["probabilities"] or {}

    if probabilities:
        probability_df = pd.DataFrame({
            "Fenomena": list(probabilities.keys()),
            "Probabilitas": list(probabilities.values())
        })
        probability_df = probability_df.sort_values(
            "Probabilitas",
            ascending=True
        )
        with st.container(border=True, key="probability_chart"):
            st.caption(
                "Grafik menunjukkan tingkat probabilitas model "
                "untuk setiap kelas fenomena."
            )
            st.bar_chart(
                probability_df.set_index("Fenomena"),
                horizontal=True,
                x_label="Probabilitas",
                y_label="Fenomena",
                color=CHART_COLOR
            )
    else:
        st.info("Informasi probabilitas tidak tersedia.")

def _display_meteorological_parameters(selected_data):
    if selected_data is None:
        return

    st.divider()
    st.subheader("🌤️ Parameter Meteorologi")

    # ---------- Baris 1: Visibility | Suhu dan Kelembapan ----------
    row1_left, row1_right = st.columns([1, 2])

    with row1_left:
        with st.container(border=True, key="visibility_card"):
            st.markdown("**👁️ Jarak Pandang**")
            st.metric(
                "Visibility (VV)",
                format_value(selected_data.get("visibility_vv"))
            )

    with row1_right:
        with st.container(border=True, key="temperature_card"):
            st.markdown("**🌡️ Suhu dan Kelembapan**")
            c1, c2, c3 = st.columns(3)

            with c1:
                st.metric(
                    "Suhu Udara",
                    format_value(
                        selected_data.get("temp_drybulb_c_tttttt"), " °C"
                    )
                )
            with c2:
                st.metric(
                    "Titik Embun",
                    format_value(
                        selected_data.get("temp_dewpoint_c_tdtdtd"), " °C"
                    )
                )
            with c3:
                st.metric(
                    "Kelembapan Relatif",
                    format_value(
                        selected_data.get("relative_humidity_pc"), " %"
                    )
                )

    # ---------- Baris 2: Angin dan Tekanan | Awan ----------
    row2_left, row2_right = st.columns([3, 2])

    with row2_left:
        with st.container(border=True, key="wind_pressure_card"):
            st.markdown("**💨 Tekanan dan Angin**")
            c1, c2, c3 = st.columns(3)

            with c1:
                st.metric(
                    "Tekanan QFF",
                    format_value(
                        selected_data.get("pressure_qff_mb_derived"), " hPa"
                    )
                )
            with c2:
                st.metric(
                    "Kecepatan Angin",
                    format_value(selected_data.get("wind_speed_ff"))
                )
            with c3:
                st.metric(
                    "Arah Angin",
                    format_value(
                        selected_data.get("wind_dir_deg_dd"), "°"
                    )
                )

    with row2_right:
        with st.container(border=True, key="cloud_card"):
            st.markdown("**☁️ Kondisi Tutupan Awan**")
            c1, c2 = st.columns(2)

            with c1:
                st.metric(
                    "Awan Rendah",
                    format_value(selected_data.get("cloud_low_cover_1"))
                )
            with c2:
                st.metric(
                    "Awan Total",
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
            "Perbandingan": COMPARISON_ICON.get(comparison, comparison)
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
    st.subheader("🕒 Riwayat Fenomena Visibility")
    st.caption(
        f"Riwayat klasifikasi selama {selected_duration} jam "
        "hingga waktu observasi yang dipilih."
    )

    timeline_df = _build_timeline(phenomenon_df, selected_tz)

    with st.container(border=True, key="timeline_card"):
        if timeline_df.empty:
            st.info(
                "Tidak ada laporan observasi pada rentang waktu "
                "yang dipilih."
            )
        else:
            # Tinggi dibatasi agar tabel tidak terlalu panjang.
            table_height = min(38 * (len(timeline_df) + 1), 420)
            st.dataframe(
                timeline_df,
                width="stretch",
                hide_index=True,
                height=table_height
            )

def _display_visibility_chart(df, selected_utc, selected_tz, selected_duration):
    st.divider()
    st.subheader("📈 Perubahan Visibility")
    st.caption(
        f"Perubahan nilai visibility selama {selected_duration} jam "
        "berdasarkan laporan observasi."
    )

    end_time = pd.Timestamp(selected_utc)
    start_time = end_time - pd.Timedelta(hours=selected_duration - 1)

    visibility_df = df[
        (df["data_timestamp"] >= start_time) &
        (df["data_timestamp"] <= end_time)
    ][["data_timestamp", "visibility_vv"]].copy()

    visibility_df = visibility_df.sort_values("data_timestamp")
    visibility_df["visibility_vv"] = pd.to_numeric(
        visibility_df["visibility_vv"], errors="coerce"
    )

    valid_values = visibility_df["visibility_vv"].dropna()

    if valid_values.empty:
        st.info("Data visibility tidak tersedia pada rentang waktu ini.")
        return

    visibility_df["Waktu"] = (
        visibility_df["data_timestamp"]
        .dt.tz_convert(selected_tz)
        .dt.tz_localize(None)
    )

    # Beri ruang kosong di atas dan bawah supaya garis tidak mentok.
    y_min, y_max = valid_values.min(), valid_values.max()
    span = y_max - y_min
    padding = span * 0.2 if span > 0 else max(abs(y_max) * 0.1, 1)
    y_domain = [max(0, y_min - padding), y_max + padding]

    chart = (
        alt.Chart(visibility_df)
        .mark_line(
            color=CHART_COLOR,
            strokeWidth=2.5,
            interpolate="monotone",  # halus tapi tidak melewati nilai maks/min
            point=alt.OverlayMarkDef(
                filled=True,
                size=70,
                color=CHART_COLOR
            )
        )
        .encode(
            x=alt.X(
                "Waktu:T",
                title="Waktu",
                axis=alt.Axis(format="%d/%m %H:%M", labelAngle=-30)
            ),
            y=alt.Y(
                "visibility_vv:Q",
                title="Nilai Visibility (VV)",
                scale=alt.Scale(domain=y_domain, nice=False, zero=False)
            ),
            tooltip=[
                alt.Tooltip("Waktu:T", title="Waktu", format="%d-%m-%Y %H:%M"),
                alt.Tooltip("visibility_vv:Q", title="VV"),
            ]
        )
        .properties(height=300)
    )

    with st.container(border=True, key="visibility_graph_chart"):
        st.markdown("**Grafik Historis Visibility**")
        st.altair_chart(chart, width="stretch")
        st.caption(
            "Nilai VV merupakan hasil decoding kode SYNOP "
            "dan tidak otomatis menunjukkan jarak dalam meter."
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

    # Divider pembuka sengaja dihapus: app.py sudah memberi divider
    # sebelum display_results() dipanggil.
    st.subheader("⚙️ Pengaturan Tampilan")

    with st.container(border=True, key="display_settings"):
        st.markdown("**Rentang Waktu Riwayat Fenomena**")

        col_duration, _ = st.columns([1, 2])
        with col_duration:
            selected_duration = st.selectbox(
                "Tampilkan riwayat selama:",
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
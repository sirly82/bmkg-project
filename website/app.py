import sys
from pathlib import Path

WEBSITE_DIR = Path(__file__).resolve().parent
if str(WEBSITE_DIR) not in sys.path:
    sys.path.insert(0, str(WEBSITE_DIR))

from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

import streamlit as st

from components.csv_handler import (
    DATASET_DIR,
    fetch_and_predict_csv,
    get_dataset_time_metadata,
    list_dataset_files,
    load_dataset_df,
)
from components.data_handler import fetch_and_predict
from components.display_classification import display_classification_results
from components.display_common import render_metric_card
from components.display_forecast import display_forecast_results
from components.style import apply_custom_style
from modules.database import DB_PATH, count_reports, get_recent_observations

# ============================================================
# 1. KONFIGURASI HALAMAN
# ============================================================
st.set_page_config(
    page_title="Weather Monitoring - BMKG Jambi",
    page_icon="🌦️",
    layout="wide",
)

apply_custom_style()

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

if "selected_mode" not in st.session_state:
    st.session_state["selected_mode"] = None
if "selected_source" not in st.session_state:
    st.session_state["selected_source"] = None

def clear_results():
    for key in ("weather_df", "result_selected_datetime", "result_timezone_label"):
        st.session_state.pop(key, None)

def clear_csv_time_selection():
    clear_results()
    for key in ("csv_manual_date", "csv_manual_hour"):
        st.session_state.pop(key, None)

def reset_workspace():
    clear_results()
    for key in (
        "timezone_label",
        "use_now",
        "manual_date",
        "manual_hour",
        "force_refresh",
        "selected_csv_file",
        "csv_manual_date",
        "csv_manual_hour",
        "selected_duration_classification",
    ):
        st.session_state.pop(key, None)

# ============================================================
# 2. HEADER
# ============================================================
st.markdown(
    """
<div class="main-header">
    <div class="header-eyebrow">BMKG • STASIUN METEOROLOGI KELAS I SULTAN THAHA JAMBI (96195)</div>
    <h1>🌦️ Weather Phenomenon Monitoring</h1>
    <p>
        Sistem klasifikasi dan prediksi 7 fenomena cuaca berbasis observasi
        SYNOP (Ogimet) serta dataset internal meteorologi.
    </p>
    <div class="chips">
        <span class="chip">🌐 Data SYNOP</span>
        <span class="chip">📂 Dataset Internal CSV</span>
        <span class="chip">🔮 Forecast (t+1) • XGBoost</span>
        <span class="chip">🎯 Classification (t) • LightGBM</span>
    </div>
</div>
""",
    unsafe_allow_html=True,
)

# ============================================================
# 3. TAHAP 1: PILIH MODE (FORECAST VS CLASSIFICATION)
# ============================================================
if st.session_state["selected_mode"] is None:
    st.write("")
    col_left, col_right = st.columns(2, gap="large")

    with col_left:
        with st.container(border=True, key="mode_card_forecast"):
            st.markdown(
                """
                <div class="mode-card-body">
                    <div class="mode-icon-box forecast-icon">🔮</div>
                    <div class="mode-title">Forecast</div>
                    <div class="mode-subtitle">
                        Prediksi fenomena cuaca 1 jam ke depan (t+1)
                    </div>
                    <span class="mode-pill forecast-pill">XGBoost • Horizon +1 Jam</span>
                </div>
                """,
                unsafe_allow_html=True,
            )
            if st.button(
                "Pilih Forecast →",
                type="primary",
                width="stretch",
                key="btn_choose_forecast",
            ):
                reset_workspace()
                st.session_state["selected_mode"] = "forecast"
                st.session_state["selected_source"] = "synop"
                st.rerun()

    with col_right:
        with st.container(border=True, key="mode_card_classification"):
            st.markdown(
                """
                <div class="mode-card-body">
                    <div class="mode-icon-box class-icon">🎯</div>
                    <div class="mode-title">Classification</div>
                    <div class="mode-subtitle">
                        Klasifikasi fenomena cuaca saat ini (t)
                    </div>
                    <span class="mode-pill class-pill">LightGBM • Monitoring</span>
                </div>
                """,
                unsafe_allow_html=True,
            )
            if st.button(
                "Pilih Classification →",
                type="primary",
                width="stretch",
                key="btn_choose_classification",
            ):
                reset_workspace()
                st.session_state["selected_mode"] = "classification"
                st.session_state["selected_source"] = "synop"
                st.rerun()

# ============================================================
# 5. TAHAP 3: WORKSPACE AKTIF (MODE + SUMBER DATA TERPILIH)
# ============================================================
else:
    mode = st.session_state["selected_mode"]
    source = st.session_state["selected_source"]
    is_forecast = mode == "forecast"
    is_synop = source == "synop"

    # Bar atas dengan tombol Ganti Dataset & Ganti Mode
    with st.container(border=True, key="active_mode_bar"):
        bar_left, bar_mid, bar_right = st.columns([3.2, 1.4, 1.1], vertical_alignment="center")
        with bar_left:
            source_badge = "Data SYNOP (Ogimet)" if is_synop else "Dataset Internal (CSV)"
            if is_forecast:
                st.markdown(f"### 🔮 Forecast (t+1) • {source_badge}")
                st.caption("Prediksi fenomena cuaca 1 jam ke depan menggunakan model XGBoost.")
            else:
                st.markdown(f"### 🎯 Classification (t) • {source_badge}")
                st.caption("Klasifikasi fenomena cuaca saat ini menggunakan model LightGBM.")

        with bar_mid:
            switch_label = (
                "⇄ Ganti ke Dataset Internal"
                if is_synop
                else "⇄ Ganti ke Data SYNOP"
            )
            if st.button(switch_label, width="stretch", key="btn_switch_source"):
                clear_results()
                st.session_state["selected_source"] = "internal" if is_synop else "synop"
                st.rerun()

        with bar_right:
            if st.button("← Ganti Mode", width="stretch", key="btn_back_to_modes"):
                reset_workspace()
                st.session_state["selected_mode"] = None
                st.session_state["selected_source"] = None
                st.rerun()

    # --------------------------------------------------------
    # WORKSPACE A: SUMBER DATA SYNOP (OGIMET)
    # --------------------------------------------------------
    if is_synop:
        with st.container(border=True, key="time_settings"):
            st.subheader("🕒 Pengaturan Waktu Observasi")
            if is_forecast:
                st.caption("Tentukan waktu basis observasi (t) untuk memprediksi 1 jam berikutnya (t+1).")
            else:
                st.caption("Tentukan tanggal, jam observasi (t), dan zona waktu pengamatan.")

            selected_timezone_label = st.selectbox(
                "Zona waktu",
                options=list(TIMEZONES.keys()),
                index=0,
                key="timezone_label",
                on_change=clear_results,
            )
            selected_tz = ZoneInfo(TIMEZONES[selected_timezone_label])
            now = datetime.now(selected_tz)

            use_now = st.checkbox("Gunakan jam sekarang", key="use_now", on_change=clear_results)

            today = now.date()
            if "manual_date" not in st.session_state or st.session_state["manual_date"] > today:
                st.session_state["manual_date"] = today

            col_date, col_time = st.columns(2)
            with col_date:
                selected_date = st.date_input(
                    "Tanggal observasi",
                    max_value=today,
                    key="manual_date",
                    disabled=use_now,
                    on_change=clear_results,
                )

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
                    disabled=use_now,
                    on_change=clear_results,
                )

            if use_now:
                candidate_datetime = now.replace(minute=0, second=0, microsecond=0)
            else:
                candidate_datetime = datetime.combine(
                    selected_date,
                    time(selected_hour, 0),
                ).replace(tzinfo=selected_tz)

            is_future = candidate_datetime > now

            st.markdown("#### Waktu terpilih")
            if is_forecast:
                forecast_candidate = candidate_datetime + timedelta(hours=1)
                col1, col2, col3 = st.columns(3, gap="medium")
                with col1:
                    render_metric_card(
                        label="📅 Tanggal Basis (t)",
                        value=candidate_datetime.strftime("%d-%m-%Y"),
                        footer="Hari observasi",
                        accent="slate",
                    )
                with col2:
                    render_metric_card(
                        label="🕒 Jam Basis (t)",
                        value=candidate_datetime.strftime("%H:%M"),
                        footer="Waktu input model",
                        accent="teal",
                    )
                with col3:
                    render_metric_card(
                        label="🔮 Target Prediksi (t+1)",
                        value=forecast_candidate.strftime("%H:%M"),
                        footer=f"📅 {forecast_candidate.strftime('%d-%m-%Y')}",
                        accent="navy",
                    )
            else:
                col1, col2 = st.columns(2, gap="medium")
                with col1:
                    st.metric("Tanggal Observasi (t)", candidate_datetime.strftime("%d-%m-%Y"))
                with col2:
                    st.metric("Jam Observasi (t)", candidate_datetime.strftime("%H:%M"))

            st.write("")
            st.caption(f"Zona waktu: {selected_timezone_label}")

            if is_future:
                st.error("Waktu observasi tidak boleh melebihi waktu saat ini.")

        selected_datetime = None if is_future else candidate_datetime

        st.write("")

        force_refresh = st.checkbox(
            "Paksa ambil ulang data terbaru dari Ogimet (abaikan cache)",
            value=False,
            key="force_refresh",
        )

        button_label = (
            "🔮 Jalankan Forecast (t+1)"
            if is_forecast
            else "🎯 Jalankan Classification (t)"
        )

        load_data = st.button(
            button_label,
            type="primary",
            disabled=selected_datetime is None,
            width="stretch",
        )

        if load_data and selected_datetime is not None:
            clear_results()
            spinner_text = (
                "Mengambil data observasi dan menjalankan forecast 1 jam ke depan..."
                if is_forecast
                else "Mengambil data observasi dan menjalankan klasifikasi..."
            )
            try:
                with st.spinner(spinner_text):
                    result_df = fetch_and_predict(
                        selected_datetime=selected_datetime,
                        selected_timezone=TIMEZONES[selected_timezone_label],
                        force_refresh=force_refresh,
                    )

                st.session_state["weather_df"] = result_df
                st.session_state["result_selected_datetime"] = selected_datetime.isoformat()
                st.session_state["result_timezone_label"] = selected_timezone_label
                st.success("Pengambilan data dan pemrosesan model selesai.")
            except Exception as error:
                st.error(f"Terjadi kesalahan saat memproses data: {error}")

    # --------------------------------------------------------
    # WORKSPACE B: SUMBER DATASET INTERNAL (bmkg-dataset/*.csv)
    # --------------------------------------------------------
    else:
        csv_files = list_dataset_files()

        with st.container(border=True, key="time_settings"):
            st.subheader("📂 Pilih Dataset & Waktu Observasi")
            st.caption(
                f"Memuat file CSV dari folder `{DATASET_DIR.name}/`. "
                "Rentang tanggal dan jam otomatis menyesuaikan isi dataset terpilih."
            )

            if not csv_files:
                st.warning(
                    f"Tidak ada file berawalan `clean` (`clean*.csv`) ditemukan di folder `{DATASET_DIR}`. "
                    "Pastikan nama file dataset diawali dengan `clean` dan berada di dalam folder `bmkg-dataset/`."
                )
                selected_csv_file = None
                selected_datetime = None
                selected_timezone_label = list(TIMEZONES.keys())[0]
            else:
                selected_csv_file = st.selectbox(
                    "File dataset CSV",
                    options=csv_files,
                    index=0,
                    key="selected_csv_file",
                    on_change=clear_csv_time_selection,
                )

                selected_timezone_label = st.selectbox(
                    "Zona waktu",
                    options=list(TIMEZONES.keys()),
                    index=0,
                    key="timezone_label",
                    on_change=clear_csv_time_selection,
                )
                selected_tz_name = TIMEZONES[selected_timezone_label]
                selected_tz = ZoneInfo(selected_tz_name)

                try:
                    df_csv = load_dataset_df(selected_csv_file)
                    meta = get_dataset_time_metadata(df_csv, selected_tz_name)
                    min_date = meta["min_date"]
                    max_date = meta["max_date"]
                    latest_local = meta["latest_local"]
                    earliest_selectable = meta["earliest_selectable_local"]
                    raw_first = meta["raw_first_local"]
                    hours_by_date = meta["hours_by_date"]

                    if meta["allow_lag_nan"]:
                        st.caption(
                            f"Waktu dapat dipilih: **{earliest_selectable.strftime('%d-%m-%Y %H:%M')}** s.d. "
                            f"**{latest_local.strftime('%d-%m-%Y %H:%M')}**."
                        )
                    else:
                        st.caption(
                            f"Waktu dapat dipilih: **{earliest_selectable.strftime('%d-%m-%Y %H:%M')}** s.d. "
                            f"**{latest_local.strftime('%d-%m-%Y %H:%M')}** "
                            f"(dimulai 3 jam setelah data pertama `{raw_first.strftime('%H:%M')}` "
                            f"untuk kebutuhan riwayat t-1 s.d. t-3)."
                        )

                    # Default tanggal ke tanggal terakhir di dataset
                    if (
                        "csv_manual_date" not in st.session_state
                        or st.session_state["csv_manual_date"] < min_date
                        or st.session_state["csv_manual_date"] > max_date
                    ):
                        st.session_state["csv_manual_date"] = max_date

                    def _on_csv_date_change():
                        clear_results()
                        st.session_state.pop("csv_manual_hour", None)

                    col_date, col_time = st.columns(2)
                    with col_date:
                        selected_date = st.date_input(
                            "Tanggal observasi",
                            min_value=min_date,
                            max_value=max_date,
                            key="csv_manual_date",
                            on_change=_on_csv_date_change,
                        )

                    available_hours = hours_by_date.get(selected_date, [])

                    with col_time:
                        if available_hours:
                            # Default jam ke jam terakhir pada tanggal tersebut
                            if (
                                "csv_manual_hour" not in st.session_state
                                or st.session_state["csv_manual_hour"] not in available_hours
                            ):
                                st.session_state["csv_manual_hour"] = available_hours[-1]

                            selected_hour = st.selectbox(
                                "Jam observasi (tersedia di dataset)",
                                options=available_hours,
                                format_func=lambda x: f"{x:02d}:00",
                                key="csv_manual_hour",
                                on_change=clear_results,
                            )
                        else:
                            st.selectbox(
                                "Jam observasi",
                                options=["Tidak tersedia"],
                                disabled=True,
                            )
                            selected_hour = None

                    if available_hours and selected_hour is not None:
                        selected_datetime = datetime.combine(
                            selected_date,
                            time(selected_hour, 0),
                        ).replace(tzinfo=selected_tz)

                        st.markdown("#### Waktu terpilih")
                        if is_forecast:
                            forecast_candidate = selected_datetime + timedelta(hours=1)
                            col1, col2, col3 = st.columns(3, gap="medium")
                            with col1:
                                render_metric_card(
                                    label="📅 Tanggal Basis (t)",
                                    value=selected_datetime.strftime("%d-%m-%Y"),
                                    footer="Hari observasi CSV",
                                    accent="slate",
                                )
                            with col2:
                                render_metric_card(
                                    label="🕒 Jam Basis (t)",
                                    value=selected_datetime.strftime("%H:%M"),
                                    footer="Waktu input model",
                                    accent="teal",
                                )
                            with col3:
                                render_metric_card(
                                    label="🔮 Target Prediksi (t+1)",
                                    value=forecast_candidate.strftime("%H:%M"),
                                    footer=f"📅 {forecast_candidate.strftime('%d-%m-%Y')}",
                                    accent="navy",
                                )
                        else:
                            col1, col2 = st.columns(2, gap="medium")
                            with col1:
                                st.metric("Tanggal Observasi (t)", selected_datetime.strftime("%d-%m-%Y"))
                            with col2:
                                st.metric("Jam Observasi (t)", selected_datetime.strftime("%H:%M"))

                        st.write("")
                        st.caption(
                            f"Zona waktu: {selected_timezone_label} • "
                            f"Data terakhir pada file ini: {latest_local.strftime('%d-%m-%Y %H:%M')}"
                        )
                    else:
                        selected_datetime = None
                        st.warning(
                            f"Tidak ada rekaman observasi pada tanggal **{selected_date.strftime('%d-%m-%Y')}** "
                            "di dalam file CSV ini. Silakan pilih tanggal lain."
                        )

                except Exception as csv_err:
                    selected_datetime = None
                    st.error(f"Gagal membaca dataset CSV: {csv_err}")

        st.write("")

        button_label = (
            "🔮 Jalankan Forecast (t+1)"
            if is_forecast
            else "🎯 Jalankan Classification (t)"
        )

        load_data = st.button(
            button_label,
            type="primary",
            disabled=selected_datetime is None,
            width="stretch",
        )

        if load_data and selected_datetime is not None and selected_csv_file is not None:
            clear_results()
            spinner_text = (
                "Memproses dataset CSV dan menjalankan forecast 1 jam ke depan..."
                if is_forecast
                else "Memproses dataset CSV dan menjalankan klasifikasi..."
            )
            try:
                with st.spinner(spinner_text):
                    result_df = fetch_and_predict_csv(
                        rel_path=selected_csv_file,
                        selected_datetime=selected_datetime,
                        selected_timezone=TIMEZONES[selected_timezone_label],
                    )

                st.session_state["weather_df"] = result_df
                st.session_state["result_selected_datetime"] = selected_datetime.isoformat()
                st.session_state["result_timezone_label"] = selected_timezone_label
                st.success("Pemrosesan dataset internal selesai.")
            except Exception as error:
                st.error(f"Terjadi kesalahan saat memproses dataset: {error}")

    # --------------------------------------------------------
    # TAMPILAN HASIL (BERLAKU UNTUK SYNOP MAUPUN DATASET INTERNAL)
    # --------------------------------------------------------
    st.divider()

    if "weather_df" in st.session_state:
        if is_forecast:
            display_forecast_results(
                df=st.session_state["weather_df"],
                selected_datetime_iso=st.session_state["result_selected_datetime"],
                selected_timezone_label=st.session_state["result_timezone_label"],
                timezones=TIMEZONES,
            )
        else:
            display_classification_results(
                df=st.session_state["weather_df"],
                selected_datetime_iso=st.session_state["result_selected_datetime"],
                selected_timezone_label=st.session_state["result_timezone_label"],
                timezones=TIMEZONES,
            )
    else:
        if is_forecast:
            st.info(
                "Hasil forecast belum tersedia. Pilih waktu basis observasi, "
                "lalu klik **Jalankan Forecast (t+1)**."
            )
        else:
            st.info(
                "Hasil klasifikasi belum tersedia. Pilih waktu observasi, "
                "lalu klik **Jalankan Classification (t)**."
            )

# ============================================================
# 5. INSPEKSI DATABASE & FOOTER
# ============================================================
if st.session_state.get("selected_source") == "synop":
    st.write("")
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

    st.divider()
    st.markdown(
        """
        <div class="custom-footer">
            Prototype Monitoring, Klasifikasi, dan Prediksi Fenomena Cuaca
            <br>
            Stasiun Meteorologi Kelas I Sultan Thaha Jambi
        </div>
        """,
        unsafe_allow_html=True,
    )
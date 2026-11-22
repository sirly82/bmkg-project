from zoneinfo import ZoneInfo

import altair as alt
import pandas as pd
import streamlit as st

CHART_COLOR = "#1F6F78"
FORECAST_CHART_COLOR = "#14324F"

def wrap_text(text):
    """Beri titik putus baris setelah '/' agar teks panjang turun baris rapi."""
    return str(text).replace("/", "/\u200b")

def render_metric_card(label, value, footer="", accent="teal", status=None):
    """Kartu metrik rata tinggi dengan bilah aksen bawah dan lencana status timbul."""
    card_class = "custom-metric-card"
    badge_html = ""

    if status == "match":
        card_class += " card-match"
        badge_html = '<div class="metric-status-badge badge-match" title="Sesuai dengan data aktual">✓</div>'
    elif status == "mismatch":
        card_class += " card-mismatch"
        badge_html = '<div class="metric-status-badge badge-mismatch" title="Berbeda dengan data aktual">!</div>'

    footer_html = (
        f'<div class="custom-metric-footer accent-{accent}">{footer}</div>'
        if footer
        else ""
    )

    html = (
        f'<div class="{card_class}">'
        f"{badge_html}"
        f'<div class="custom-metric-body">'
        f'<div class="custom-metric-label">{label}</div>'
        f'<div class="custom-metric-value">{value}</div>'
        f"</div>"
        f"{footer_html}"
        f"</div>"
    )
    st.markdown(html, unsafe_allow_html=True)

def format_value(value, suffix=""):
    """Mengubah nilai menjadi teks yang mudah dibaca."""
    if pd.isna(value):
        return "-"
    return f"{value}{suffix}"

def format_oktas(value):
    """Tutupan awan dalam okta; kode 9 = langit tidak terlihat."""
    if pd.isna(value):
        return "-"
    try:
        okta = int(float(value))
    except (TypeError, ValueError):
        return str(value)
    if okta == 9:
        return "9 (langit tak terlihat)"
    return f"{okta} okta"

def format_km(value):
    """Visibility dalam km: 4.0 -> '4 km', 0.5 -> '0,5 km'."""
    if pd.isna(value):
        return "-"
    return f"{float(value):g} km".replace(".", ",")

def get_observed_phenomenon(row):
    """
    Mengambil fenomena aktual berdasarkan kode WW dan ix_flag.
    Ketiadaan kode WW tidak otomatis dianggap sebagai Normal.
    """
    ix_flag = row.get("ix_flag")

    if pd.notna(ix_flag):
        try:
            ix_flag = int(ix_flag)
        except (TypeError, ValueError):
            ix_flag = None

    if ix_flag in [2, 5]:
        return "Tidak ada Fenomena Signifikan"

    if ix_flag in [3, 6]:
        return "Tidak tersedia"

    phenomenon = row.get("phenomenon")
    if pd.notna(phenomenon) and str(phenomenon).strip() not in ("", "Unknown"):
        return str(phenomenon)

    return "Tidak tersedia"

def format_synop_footer(row):
    """Membuat keterangan footer kartu Aktual berdasarkan kode ix dan WW."""
    if row is None:
        return "Laporan Observasi"

    ix_raw = row.get("ix_flag")
    ww_raw = row.get("weather_code_ww")

    ix_val = None
    if pd.notna(ix_raw) and str(ix_raw).strip() != "":
        try:
            ix_val = int(float(ix_raw))
        except (TypeError, ValueError):
            ix_val = None

    ww_str = None
    if pd.notna(ww_raw) and str(ww_raw).strip() not in ("", "None", "nan"):
        raw_text = str(ww_raw).strip()
        try:
            ww_str = f"{int(float(raw_text)):02d}"
        except (TypeError, ValueError):
            ww_str = raw_text

    if ix_val in (1, 4):
        if ww_str:
            return f"Kode WW: {ww_str} • ix: {ix_val}"
        return f"Kode ix: {ix_val} (Kelompok 7wwW1W2)"

    if ix_val in (2, 5):
        return f"Kode ix: {ix_val}"

    if ix_val in (3, 6):
        return f"Kode ix: {ix_val}"

    if ww_str:
        return f"Kode WW: {ww_str}"

    return "Laporan Observasi"

def compare_prediction(predicted, observed):
    if observed == "Tidak ada Fenomena Signifikan":
        return "Sesuai" if predicted == "Normal" else "Berbeda"

    if observed == "Tidak tersedia":
        return "Tidak dapat dibandingkan"

    return "Sesuai" if predicted == observed else "Berbeda"

def get_comparison_status(predicted, observed):
    """Mengembalikan 'match', 'mismatch', atau None untuk lencana kartu."""
    result = compare_prediction(predicted, observed)
    if result == "Sesuai":
        return "match"
    if result == "Berbeda":
        return "mismatch"
    return None

COMPARISON_ICON = {
    "Sesuai": "✅ Sesuai",
    "Berbeda": "⚠️ Berbeda",
    "Tidak dapat dibandingkan": "➖ Tidak dapat dibandingkan",
}

def prepare_observation_context(
    df,
    selected_datetime_iso,
    selected_timezone_label,
    timezones,
):
    """
    Menyiapkan DataFrame terurut, timestamp target (UTC & lokal),
    serta baris observasi terpilih (dengan fallback maks 3 jam jika belum rilis).
    """
    selected_tz = ZoneInfo(timezones[selected_timezone_label])
    ts_local = pd.Timestamp(selected_datetime_iso)
    if ts_local.tzinfo is None:
        ts_local = ts_local.tz_localize(selected_tz)
    else:
        ts_local = ts_local.tz_convert(selected_tz)

    target_local = ts_local.floor("h")
    selected_utc = target_local.tz_convert("UTC")

    clean_df = df.copy()
    clean_df["data_timestamp"] = pd.to_datetime(clean_df["data_timestamp"], utc=True)
    clean_df = clean_df.sort_values("data_timestamp").reset_index(drop=True)

    available_up_to_target = clean_df[clean_df["data_timestamp"] <= selected_utc]
    selected_row = available_up_to_target[
        available_up_to_target["data_timestamp"] == selected_utc
    ]

    fallback_info = None

    if not selected_row.empty:
        selected_data = selected_row.iloc[0]
    elif not available_up_to_target.empty:
        latest_row = available_up_to_target.iloc[-1]
        gap = selected_utc - latest_row["data_timestamp"]
        latest_local = latest_row["data_timestamp"].tz_convert(selected_tz)

        if gap <= pd.Timedelta(hours=3):
            selected_data = latest_row
            fallback_info = {
                "used_fallback": True,
                "target_local": target_local,
                "actual_local": latest_local,
                "gap_hours": int(gap.total_seconds() // 3600),
            }
        else:
            selected_data = None
            fallback_info = {
                "used_fallback": False,
                "target_local": target_local,
                "latest_local": latest_local,
            }
    else:
        selected_data = None

    return {
        "df": clean_df,
        "selected_tz": selected_tz,
        "target_local": target_local,
        "selected_utc": selected_utc,
        "selected_data": selected_data,
        "fallback_info": fallback_info,
    }

def display_probability_chart(probabilities, title, caption, color, key_suffix):
    st.divider()
    st.subheader(title)
    st.caption(caption)

    if not probabilities:
        st.info("Informasi probabilitas tidak tersedia.")
        return

    probability_df = pd.DataFrame({
        "Fenomena": list(probabilities.keys()),
        "Probabilitas": [float(v) for v in probabilities.values()],
    }).sort_values("Probabilitas", ascending=False).reset_index(drop=True)

    probability_df["Label"] = probability_df["Probabilitas"].map(lambda v: f"{v:.2%}")
    probability_df["IsTop"] = probability_df.index == 0
    probability_df.attrs = {}

    max_prob = float(probability_df["Probabilitas"].max()) if not probability_df.empty else 1.0
    x_upper = min(1.12, max(max_prob * 1.18, 0.15))

    base = alt.Chart(probability_df).encode(
        x=alt.X(
            "Probabilitas:Q",
            title="Probabilitas",
            axis=alt.Axis(format=".0%", grid=True),
            scale=alt.Scale(domain=[0, x_upper], nice=False),
        ),
        y=alt.Y(
            "Fenomena:N",
            title=None,
            sort="-x",
            axis=alt.Axis(
                labelLimit=260,
                labelPadding=14,
                labelFontSize=12.5,
                labelColor="#1F2D3D",
                ticks=False,
                domainColor="#D3DCE4",
            ),
        ),
        tooltip=[
            alt.Tooltip("Fenomena:N", title="Fenomena"),
            alt.Tooltip("Label:N", title="Probabilitas"),
        ],
    )

    bars = base.mark_bar(
        cornerRadiusTopRight=6,
        cornerRadiusBottomRight=6,
        height=24,
        color=color,
    ).encode(
        opacity=alt.condition(alt.datum.IsTop, alt.value(1.0), alt.value(0.55)),
    )

    labels = base.mark_text(
        align="left",
        baseline="middle",
        dx=8,
        fontSize=12,
        fontWeight="bold",
        color="#1F2D3D",
    ).encode(
        text="Label:N",
    )

    chart = (
        (bars + labels)
        .properties(
            height=330,
            padding={"left": 28, "right": 24, "top": 12, "bottom": 12},
        )
        .configure_view(strokeWidth=0)
    )

    with st.container(border=True, key=f"probability_chart_{key_suffix}"):
        st.altair_chart(chart, width="stretch")

def is_internal_source(df=None):
    """Mengecek apakah data berasal dari dataset internal CSV."""
    if df is not None and getattr(df, "attrs", None):
        if df.attrs.get("dataset_source") == "internal":
            return True
    return st.session_state.get("selected_source") == "internal"

def render_model_error_notice(raw_error, mode="classification", df=None):
    """Menampilkan pesan yang rapi saat klasifikasi atau forecast gagal dijalankan."""
    action_label = "Forecast (t+1)" if mode == "forecast" else "Klasifikasi"
    err_text = str(raw_error or "").strip()
    internal = is_internal_source(df)

    is_lag_missing = any(
        token in err_text
        for token in ("_lag1", "_lag2", "_lag3", "_diff_1", "_diff_3", "riwayat jam sebelumnya")
    )

    if is_lag_missing:
        saran = (
            "💡 **Saran:** Jika Anda memilih jam-jam paling awal pada dataset internal, "
            "silakan pilih waktu observasi minimal **3 jam setelah data pertama** "
            "(atau pastikan tidak ada jam yang terlewat di dalam file CSV)."
            if internal
            else "💡 **Saran:** Pastikan laporan SYNOP pada jam terpilih dan **3 jam sebelumnya** "
            "sudah tersedia lengkap, atau coba pilih jam observasi lain."
        )
        st.warning(
            f"**{action_label} tidak dapat dilakukan**\n\n"
            "Input model harus memiliki data observasi lengkap pada jam terpilih (**t**) "
            "beserta **3 data jam sebelumnya** (**t-1**, **t-2**, dan **t-3**) untuk menghitung "
            "perubahan parameter cuaca.\n\n"
            f"{saran}"
        )
        return

    if "tidak lengkap" in err_text or "Fitur kosong:" in err_text:
        st.warning(
            f"**{action_label} tidak dapat dilakukan**\n\n"
            f"{err_text} Sebagian unsur cuaca utama (suhu, titik embun, kelembapan, tekanan, "
            "angin, atau jarak pandang) bernilai kosong sehingga model tidak dapat dijalankan."
        )
        return

    st.warning(f"**{action_label} tidak dapat dilakukan**\n\n{err_text}")

def display_meteorological_parameters(selected_data, caption=None):
    st.divider()
    st.subheader("🌡️ Parameter Meteorologi Saat Ini (t)")
    if caption:
        st.caption(caption)
    elif is_internal_source():
        st.caption("Nilai unsur-unsur cuaca pada jam observasi terpilih dari dataset internal.")
    else:
        st.caption("Nilai unsur-unsur cuaca hasil decoding sandi SYNOP pada jam observasi terpilih.")

    if selected_data is None:
        st.info("Data parameter meteorologi tidak tersedia pada jam observasi ini.")
        return

    row1_left, row1_right = st.columns([1, 2])

    with row1_left:
        with st.container(border=True, key="visibility_card"):
            st.markdown("**👁️ Jarak Pandang**")
            st.metric(
                "Visibility (VV)",
                format_km(selected_data.get("visibility_vv")),
            )

    with row1_right:
        with st.container(border=True, key="temperature_card"):
            st.markdown("**🌡️ Suhu dan Kelembapan**")
            c1, c2, c3 = st.columns(3)

            with c1:
                st.metric(
                    "Suhu Udara",
                    format_value(selected_data.get("temp_drybulb_c_tttttt"), " °C"),
                )
            with c2:
                st.metric(
                    "Titik Embun",
                    format_value(selected_data.get("temp_dewpoint_c_tdtdtd"), " °C"),
                )
            with c3:
                st.metric(
                    "Kelembapan Relatif",
                    format_value(selected_data.get("relative_humidity_pc"), " %"),
                )

    row2_left, row2_right = st.columns([3, 2])

    with row2_left:
        with st.container(border=True, key="wind_pressure_card"):
            st.markdown("**💨 Tekanan dan Angin**")
            c1, c2, c3 = st.columns(3)

            with c1:
                st.metric(
                    "Tekanan QFF",
                    format_value(selected_data.get("pressure_qff_mb_derived"), " hPa"),
                )
            with c2:
                st.metric(
                    "Kecepatan Angin",
                    format_value(selected_data.get("wind_speed_ff"), " knot"),
                )
            with c3:
                st.metric(
                    "Arah Angin",
                    format_value(selected_data.get("wind_dir_deg_dd"), "°"),
                )

    with row2_right:
        with st.container(border=True, key="cloud_card"):
            st.markdown("**☁️ Kondisi Tutupan Awan**")
            c1, c2 = st.columns(2)

            with c1:
                st.metric(
                    "Awan Rendah",
                    format_oktas(selected_data.get("cloud_low_cover_oktas")),
                )
            with c2:
                st.metric(
                    "Awan Menengah",
                    format_oktas(selected_data.get("cloud_med_cover_oktas")),
                )

def _build_single_series_chart(df_local, col_name, y_title, unit_label, color):
    series_df = df_local[["Waktu", col_name]].copy()
    series_df[col_name] = pd.to_numeric(series_df[col_name], errors="coerce")
    valid = series_df[col_name].dropna()

    if valid.empty:
        return None

    y_min, y_max = float(valid.min()), float(valid.max())
    span = y_max - y_min
    padding = span * 0.2 if span > 0 else max(abs(y_max) * 0.1, 1.0)
    y_domain = [max(0.0, y_min - padding), y_max + padding]

    return (
        alt.Chart(series_df)
        .mark_line(
            color=color,
            strokeWidth=2.5,
            interpolate="monotone",
            point=alt.OverlayMarkDef(filled=True, size=65, color=color),
        )
        .encode(
            x=alt.X(
                "Waktu:T",
                title="Waktu",
                axis=alt.Axis(format="%d/%m %H:%M", labelAngle=-30),
            ),
            y=alt.Y(
                f"{col_name}:Q",
                title=y_title,
                scale=alt.Scale(domain=y_domain, nice=False, zero=False),
            ),
            tooltip=[
                alt.Tooltip("Waktu:T", title="Waktu", format="%d-%m-%Y %H:%M"),
                alt.Tooltip(f"{col_name}:Q", title=f"{y_title} ({unit_label})"),
            ],
        )
        .properties(
            height=300,
            padding={"left": 12, "right": 20, "top": 12, "bottom": 8},
        )
    )

def _build_temp_dewpoint_chart(df_local):
    temp_df = df_local[["Waktu", "temp_drybulb_c_tttttt", "temp_dewpoint_c_tdtdtd"]].copy()
    temp_df["Suhu Udara"] = pd.to_numeric(temp_df["temp_drybulb_c_tttttt"], errors="coerce")
    temp_df["Titik Embun"] = pd.to_numeric(temp_df["temp_dewpoint_c_tdtdtd"], errors="coerce")

    melted = temp_df.melt(
        id_vars=["Waktu"],
        value_vars=["Suhu Udara", "Titik Embun"],
        var_name="Parameter",
        value_name="Nilai",
    ).dropna(subset=["Nilai"])

    if melted.empty:
        return None

    y_min, y_max = float(melted["Nilai"].min()), float(melted["Nilai"].max())
    span = y_max - y_min
    padding = span * 0.2 if span > 0 else 1.5
    y_domain = [y_min - padding, y_max + padding]

    return (
        alt.Chart(melted)
        .mark_line(
            strokeWidth=2.5,
            interpolate="monotone",
            point=alt.OverlayMarkDef(filled=True, size=65),
        )
        .encode(
            x=alt.X(
                "Waktu:T",
                title="Waktu",
                axis=alt.Axis(format="%d/%m %H:%M", labelAngle=-30),
            ),
            y=alt.Y(
                "Nilai:Q",
                title="Temperatur (°C)",
                scale=alt.Scale(domain=y_domain, nice=False, zero=False),
            ),
            color=alt.Color(
                "Parameter:N",
                title=None,
                scale=alt.Scale(
                    domain=["Suhu Udara", "Titik Embun"],
                    range=["#C98A4B", CHART_COLOR],
                ),
                legend=alt.Legend(orient="top"),
            ),
            tooltip=[
                alt.Tooltip("Waktu:T", title="Waktu", format="%d-%m-%Y %H:%M"),
                alt.Tooltip("Parameter:N", title="Parameter"),
                alt.Tooltip("Nilai:Q", title="Nilai (°C)", format=".1f"),
            ],
        )
        .properties(
            height=300,
            padding={"left": 12, "right": 20, "top": 8, "bottom": 8},
        )
    )

def display_visibility_chart(df, selected_utc, selected_tz, selected_duration):
    """Menampilkan grafik historis multi-parameter meteorologi dalam tab."""
    st.divider()
    st.subheader("📈 Grafik Historis Parameter Cuaca")
    source_desc = (
        "berdasarkan dataset internal BMKG."
        if is_internal_source(df)
        else "berdasarkan laporan observasi SYNOP."
    )
    st.caption(
        f"Perubahan unsur-unsur meteorologi selama {selected_duration} jam {source_desc}"
    )

    end_time = pd.Timestamp(selected_utc)
    start_time = end_time - pd.Timedelta(hours=selected_duration - 1)

    plot_cols = [
        "data_timestamp",
        "visibility_vv",
        "temp_drybulb_c_tttttt",
        "temp_dewpoint_c_tdtdtd",
        "relative_humidity_pc",
        "wind_speed_ff",
        "pressure_qff_mb_derived",
    ]
    available_cols = [c for c in plot_cols if c in df.columns]

    hist_df = (
        df[(df["data_timestamp"] >= start_time) & (df["data_timestamp"] <= end_time)][
            available_cols
        ]
        .sort_values("data_timestamp")
        .copy()
    )
    hist_df.attrs = {}

    if hist_df.empty:
        st.info("Data observasi tidak tersedia pada rentang waktu ini.")
        return

    hist_df["Waktu"] = (
        hist_df["data_timestamp"].dt.tz_convert(selected_tz).dt.tz_localize(None)
    )

    with st.container(border=True, key="visibility_graph_chart"):
        tab_vis, tab_temp, tab_rh, tab_wind, tab_press = st.tabs([
            "👁️ Visibility",
            "🌡️ Suhu & Titik Embun",
            "💧 Kelembapan (RH)",
            "💨 Kecepatan Angin",
            "⏲️ Tekanan QFF",
        ])

        with tab_vis:
            chart = _build_single_series_chart(
                hist_df, "visibility_vv", "Visibility (km)", "km", CHART_COLOR
            )
            if chart is not None:
                st.altair_chart(chart, width="stretch")
                st.caption("Jarak pandang mendatar dalam kilometer (hasil decoding VV).")
            else:
                st.info("Data visibility tidak tersedia pada rentang waktu ini.")

        with tab_temp:
            chart = _build_temp_dewpoint_chart(hist_df)
            if chart is not None:
                st.altair_chart(chart, width="stretch")
                st.caption("Perbandingan suhu udara (dry-bulb) dan suhu titik embun (°C).")
            else:
                st.info("Data suhu tidak tersedia pada rentang waktu ini.")

        with tab_rh:
            chart = _build_single_series_chart(
                hist_df, "relative_humidity_pc", "Kelembapan Relatif (%)", "%", "#2B8A8F"
            )
            if chart is not None:
                st.altair_chart(chart, width="stretch")
                st.caption("Persentase kelembapan relatif udara (%).")
            else:
                st.info("Data kelembapan relatif tidak tersedia pada rentang waktu ini.")

        with tab_wind:
            chart = _build_single_series_chart(
                hist_df, "wind_speed_ff", "Kecepatan Angin (knot)", "knot", "#5C84AD"
            )
            if chart is not None:
                st.altair_chart(chart, width="stretch")
                st.caption("Kecepatan angin permukaan dalam satuan knot.")
            else:
                st.info("Data kecepatan angin tidak tersedia pada rentang waktu ini.")

        with tab_press:
            chart = _build_single_series_chart(
                hist_df, "pressure_qff_mb_derived", "Tekanan QFF (hPa)", "hPa", FORECAST_CHART_COLOR
            )
            if chart is not None:
                st.altair_chart(chart, width="stretch")
                st.caption("Tekanan udara permukaan laut (QFF) dalam hPa / mb.")
            else:
                st.info("Data tekanan QFF tidak tersedia pada rentang waktu ini.")

def display_raw_and_export(
    df,
    selected_data,
    selected_utc,
    selected_tz,
    key_prefix="",
    forecast_1h=None,
):
    internal = is_internal_source(df)
    expander_title = (
        "📊 Pratinjau Data Observasi & Hasil Model"
        if internal
        else "🔍 Detail Sandi SYNOP Mentah & Ekspor Data"
    )

    st.divider()
    with st.expander(expander_title):
        if not internal:
            if selected_data is not None:
                obs_utc = pd.Timestamp(selected_data["data_timestamp"])
                obs_local = obs_utc.tz_convert(selected_tz)
                ww_val = selected_data.get("weather_code_ww")
                ix_val = selected_data.get("ix_flag")

                st.markdown(
                    f"**Waktu Observasi:** `{obs_local.strftime('%d-%m-%Y %H:%M')}` "
                    f"(`{obs_utc.strftime('%H:%M UTC')}`) | "
                    f"**Kode WW:** `{ww_val if pd.notna(ww_val) else '-'}` | "
                    f"**Indikator ix:** `{ix_val if pd.notna(ix_val) else '-'}`"
                )

                raw_synop = selected_data.get("raw_synop")
                if pd.notna(raw_synop):
                    st.code(str(raw_synop), language="text")
                else:
                    st.info("Sandi SYNOP mentah tidak tersedia.")
            else:
                st.info("Tidak ada sandi SYNOP terpilih pada jam observasi ini.")

        export_df = df.copy()
        export_df.attrs = {}

        # Hapus kolom khusus sandi SYNOP saat memakai dataset internal
        if internal:
            synop_only_cols = ["synop_type", "raw_synop"]
            if "station_id" in export_df.columns and export_df["station_id"].isna().all():
                synop_only_cols.append("station_id")
            export_df = export_df.drop(columns=synop_only_cols, errors="ignore")

        if key_prefix == "forecast" and isinstance(forecast_1h, dict):
            # Ambil hanya baris jam basis (t)
            base_raw = forecast_1h.get("base_timestamp_utc_iso")
            if base_raw:
                base_ts = pd.Timestamp(base_raw, tz="UTC")
                export_df = export_df[export_df["data_timestamp"] == base_ts].copy()
            elif selected_data is not None:
                export_df = export_df[
                    export_df["data_timestamp"] == pd.Timestamp(selected_data["data_timestamp"])
                ].copy()
            else:
                export_df = export_df.iloc[0:0].copy()

            export_df = export_df.reset_index(drop=True)
            export_df = export_df.drop(columns=["prediction_result"], errors="ignore")
            export_df.insert(0, "row_role", "basis_t")

            # Tambahkan baris aktual t+1 jika tersedia
            actual_next = forecast_1h.get("actual_next_hour")
            if isinstance(actual_next, dict) and actual_next.get("data_timestamp_iso"):
                next_row = {"row_role": "actual_t_plus_1"}
                for col in export_df.columns:
                    if col == "row_role":
                        continue
                    if col == "data_timestamp":
                        next_row[col] = pd.Timestamp(actual_next["data_timestamp_iso"])
                    elif col == "timestamp_local" and actual_next.get("timestamp_local_iso"):
                        next_row[col] = pd.Timestamp(actual_next["timestamp_local_iso"])
                    else:
                        next_row[col] = actual_next.get(col)

                export_df = pd.concat([export_df, pd.DataFrame([next_row])], ignore_index=True)

            # Sisipkan ringkasan hasil prediksi t+1
            actual_label = (
                get_observed_phenomenon(actual_next)
                if isinstance(actual_next, dict)
                else None
            )
            export_df["forecast_1h_target_utc"] = None
            export_df["forecast_1h_predicted"] = None
            export_df["forecast_1h_confidence"] = None
            export_df["forecast_1h_actual"] = None

            if not export_df.empty:
                fc_target_raw = forecast_1h.get("forecast_timestamp_utc_iso")
                export_df.loc[0, "forecast_1h_target_utc"] = (
                    pd.Timestamp(fc_target_raw).strftime("%Y-%m-%d %H:%M:%S UTC")
                    if fc_target_raw
                    else None
                )
                export_df.loc[0, "forecast_1h_predicted"] = forecast_1h.get("predicted_class")
                export_df.loc[0, "forecast_1h_confidence"] = forecast_1h.get("confidence")
                export_df.loc[0, "forecast_1h_actual"] = actual_label

            btn_label = "⬇️ Unduh Data Basis (t) & Aktual (t+1) (CSV)"
            mode_prefix = "forecast"
        else:
            if "prediction_result" in export_df.columns:
                export_df["classified_phenomenon"] = export_df["prediction_result"].apply(
                    lambda r: r.get("predicted_class") if isinstance(r, dict) else None
                )
                export_df["classification_confidence"] = export_df["prediction_result"].apply(
                    lambda r: r.get("confidence") if isinstance(r, dict) else None
                )
                export_df = export_df.drop(columns=["prediction_result"])

            btn_label = "⬇️ Unduh Data Observasi & Klasifikasi 24 Jam (CSV)"
            mode_prefix = "classification"

        if not export_df.empty and "data_timestamp" in export_df.columns:
            export_df["data_timestamp"] = pd.to_datetime(
                export_df["data_timestamp"], utc=True
            ).dt.strftime("%Y-%m-%d %H:%M:%S UTC")

        if internal:
            st.dataframe(export_df, width="stretch", hide_index=True)
        else:
            csv_bytes = export_df.to_csv(index=False).encode("utf-8")
            st.download_button(
                label=btn_label,
                data=csv_bytes,
                file_name=f"{mode_prefix}_synop_96195_{selected_utc.strftime('%Y%m%d_%H%M')}UTC.csv",
                mime="text/csv",
                key=f"download_csv_{key_prefix}",
            )
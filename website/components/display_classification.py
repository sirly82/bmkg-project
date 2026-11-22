import pandas as pd
import streamlit as st

from components.display_common import (
    CHART_COLOR,
    COMPARISON_ICON,
    compare_prediction,
    display_meteorological_parameters,
    display_probability_chart,
    display_raw_and_export,
    display_visibility_chart,
    format_synop_footer,
    get_comparison_status,
    get_observed_phenomenon,
    is_internal_source,
    prepare_observation_context,
    render_metric_card,
    render_model_error_notice,
)

def _render_classification_summary(selected_data, fallback_info=None):
    st.subheader("🎯 Hasil Klasifikasi Fenomena Cuaca (Saat Ini / t)")
    st.caption(
        "Klasifikasi kondisi cuaca pada jam observasi terpilih menggunakan model LightGBM."
    )

    if selected_data is None:
        if fallback_info and fallback_info.get("latest_local") is not None:
            latest_str = fallback_info["latest_local"].strftime("%d-%m-%Y %H:%M")
            target_str = fallback_info["target_local"].strftime("%H:%M")
            st.warning(
                f"Laporan observasi pada pukul **{target_str}** belum tersedia di Ogimet. "
                f"Laporan terakhir yang tercatat adalah **{latest_str}** "
                "(lebih dari 3 jam lalu), sehingga klasifikasi utama tidak ditampilkan. "
                "Riwayat data yang tersedia tetap dapat dilihat di bawah."
            )
        else:
            st.warning(
                "Laporan observasi pada jam yang dipilih tidak ditemukan. "
                "Riwayat data yang tersedia tetap dapat ditampilkan."
            )
        return None

    if fallback_info and fallback_info.get("used_fallback"):
        target_str = fallback_info["target_local"].strftime("%H:%M")
        actual_str = fallback_info["actual_local"].strftime("%d-%m-%Y %H:%M")
        gap_hours = fallback_info["gap_hours"]
        st.info(
            f"ℹ️ Laporan pukul **{target_str}** belum masuk ke Ogimet. "
            f"Menampilkan data dan hasil klasifikasi dari laporan terakhir yang tersedia "
            f"pada **{actual_str}** (selisih {gap_hours} jam)."
        )

    result = selected_data["prediction_result"]

    err = result.get("error")
    if err:
        render_model_error_notice(err, mode="classification")
        return

    predicted_class = result["predicted_class"]
    confidence = result["confidence"]
    observed = get_observed_phenomenon(selected_data)
    clf_status = get_comparison_status(predicted_class, observed)
    ww_footer = format_synop_footer(selected_data)

    with st.container(border=True, key="prediction_summary"):
        col1, col2, col3 = st.columns([1.3, 0.95, 1.3], gap="medium")

        with col1:
            render_metric_card(
                label="🌫️ Hasil Klasifikasi (t)",
                value=predicted_class,
                footer="Model LightGBM",
                accent="teal",
                status=clf_status,
            )
        with col2:
            render_metric_card(
                label="🎯 Tingkat Kepercayaan",
                value=f"{confidence:.2%}",
                footer="Probabilitas tertinggi",
                accent="navy",
            )
        with col3:
            render_metric_card(
                label="📋 Fenomena Aktual (WW)",
                value=observed,
                footer=ww_footer,
                accent="slate",
            )

        st.write("")

        if observed == "Tidak tersedia":
            if is_internal_source():
                st.info("ℹ️ Data fenomena aktual (WW) tidak tersedia pada rekaman dataset ini.")
            else:
                st.info("ℹ️ Data fenomena aktual (WW) tidak tersedia pada laporan SYNOP ini.")
        else:
            comp = compare_prediction(predicted_class, observed)
            if comp == "Sesuai":
                st.success("✅ **Sesuai** — Hasil klasifikasi model sesuai dengan fenomena aktual.")
            elif comp == "Berbeda":
                st.warning("⚠️ **Berbeda** — Hasil klasifikasi model berbeda dengan fenomena aktual.")
            else:
                st.info("ℹ️ Data aktual tidak dapat dibandingkan.")

    return result["probabilities"]

def _build_timeline(phenomenon_df, selected_tz):
    timeline_rows = []

    for _, row in phenomenon_df.iterrows():
        timestamp_local = row["data_timestamp"].tz_convert(selected_tz)
        result = row["prediction_result"]

        if result["error"] is None:
            predicted = result["predicted_class"]
        else:
            predicted = "Klasifikasi tidak tersedia"

        observed = get_observed_phenomenon(row)

        if predicted == "Klasifikasi tidak tersedia":
            comparison = "Tidak dapat dibandingkan"
        else:
            comparison = compare_prediction(predicted, observed)

        timeline_rows.append({
            "Waktu": timestamp_local.strftime("%d-%m-%Y %H:%M"),
            "Klasifikasi Model": predicted,
            "Fenomena Aktual (WW)": observed,
            "Perbandingan": COMPARISON_ICON.get(comparison, comparison),
        })

    out = pd.DataFrame(timeline_rows)
    out.attrs = {}
    return out

def _render_timeline(df, selected_utc, selected_tz, selected_duration):
    end_time = pd.Timestamp(selected_utc)
    start_time = end_time - pd.Timedelta(hours=selected_duration - 1)

    phenomenon_df = (
        df[
            (df["data_timestamp"] >= start_time)
            & (df["data_timestamp"] <= end_time)
        ]
        .sort_values("data_timestamp")
        .reset_index(drop=True)
    )
    phenomenon_df.attrs = {}

    st.subheader("🕒 Riwayat Klasifikasi Fenomena")
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
            table_height = min(38 * (len(timeline_df) + 1), 420)
            st.dataframe(
                timeline_df,
                width="stretch",
                hide_index=True,
                height=table_height,
            )

def display_classification_results(
    df,
    selected_datetime_iso,
    selected_timezone_label,
    timezones,
):
    """Tampilan khusus mode Klasifikasi Fenomena Cuaca (Saat Ini / t)."""
    if df is None or df.empty:
        st.warning("Data hasil pengamatan tidak tersedia.")
        return

    ctx = prepare_observation_context(
        df=df,
        selected_datetime_iso=selected_datetime_iso,
        selected_timezone_label=selected_timezone_label,
        timezones=timezones,
    )

    clf_probs = _render_classification_summary(
        selected_data=ctx["selected_data"],
        fallback_info=ctx["fallback_info"],
    )

    display_probability_chart(
        probabilities=clf_probs,
        title="📊 Probabilitas Setiap Kelas (Klasifikasi t)",
        caption="Tingkat probabilitas model LightGBM untuk setiap kelas fenomena pada jam observasi terpilih.",
        color=CHART_COLOR,
        key_suffix="t",
    )

    param_caption = (
        "Nilai unsur-unsur cuaca pada jam observasi terpilih dari dataset internal."
        if is_internal_source(ctx["df"])
        else "Nilai unsur-unsur cuaca hasil decoding sandi SYNOP pada jam observasi terpilih."
    )
    display_meteorological_parameters(ctx["selected_data"], caption=param_caption)

    st.divider()
    st.subheader("⚙️ Pengaturan Rentang Riwayat")

    with st.container(border=True, key="display_settings"):
        st.markdown("**Rentang Waktu Riwayat Fenomena**")
        col_duration, _ = st.columns([1, 2])
        with col_duration:
            selected_duration = st.selectbox(
                "Tampilkan riwayat selama:",
                options=[24, 12, 6, 3],
                format_func=lambda x: f"{x} jam terakhir",
                index=0,
                key="selected_duration_classification",
            )

    _render_timeline(
        df=ctx["df"],
        selected_utc=ctx["selected_utc"],
        selected_tz=ctx["selected_tz"],
        selected_duration=selected_duration,
    )

    display_visibility_chart(
        df=ctx["df"],
        selected_utc=ctx["selected_utc"],
        selected_tz=ctx["selected_tz"],
        selected_duration=selected_duration,
    )

    display_raw_and_export(
        df=ctx["df"],
        selected_data=ctx["selected_data"],
        selected_utc=ctx["selected_utc"],
        selected_tz=ctx["selected_tz"],
        key_prefix="classification",
    )
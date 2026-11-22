import pandas as pd
import streamlit as st

from components.display_common import (
    FORECAST_CHART_COLOR,
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

def _render_forecast_summary(forecast_1h):
    st.subheader("🔮 Hasil Prediksi Fenomena Cuaca (1 Jam ke Depan / t+1)")

    if not forecast_1h:
        st.info("Informasi prediksi 1 jam ke depan tidak tersedia.")
        return None

    base_raw = forecast_1h.get("base_timestamp_local_iso") or forecast_1h.get("base_timestamp_local")
    target_raw = forecast_1h.get("forecast_timestamp_local_iso") or forecast_1h.get("forecast_timestamp_local")

    if not base_raw or not target_raw:
        err = forecast_1h.get("error")
        if err:
            render_model_error_notice(err, mode="forecast")
        else:
            st.info("Informasi waktu prediksi 1 jam ke depan tidak tersedia.")
        return None

    base_local = pd.Timestamp(base_raw)
    target_local = pd.Timestamp(target_raw)

    st.caption(
        f"Prediksi kondisi cuaca pada **{target_local.strftime('%d-%m-%Y %H:%M')}** "
        f"berdasarkan observasi dan fenomena pukul **{base_local.strftime('%H:%M')}** "
        "menggunakan model XGBoost."
    )

    if forecast_1h.get("used_fallback"):
        st.info(
            f"ℹ️ Menggunakan laporan terakhir yang tersedia pada "
            f"**{base_local.strftime('%d-%m-%Y %H:%M')}** sebagai basis prediksi."
        )

    err = forecast_1h.get("error")
    if err:
        render_model_error_notice(err, mode="forecast")
        return None

    internal = is_internal_source()
    predicted_next = forecast_1h["predicted_class"]
    confidence_next = forecast_1h["confidence"]
    current_phenomenon = forecast_1h.get("input_phenomenon_t") or "Tidak tersedia"
    input_source = forecast_1h.get("input_phenomenon_source")

    if input_source == "classified_fallback":
        obs_footer_t = "Klasifikasi model (WW kosong)"
    elif internal:
        obs_footer_t = f"Dataset internal pukul {base_local.strftime('%H:%M')}"
    else:
        obs_footer_t = f"Observasi SYNOP pukul {base_local.strftime('%H:%M')}"

    actual_card_label = "📋 Aktual Dataset (t+1)" if internal else "📋 Aktual SYNOP (t+1)"
    actual_next = forecast_1h.get("actual_next_hour")

    if actual_next:
        observed_next = get_observed_phenomenon(actual_next)
        actual_footer = format_synop_footer(actual_next)
    else:
        observed_next = "Belum tersedia"
        actual_footer = (
            "Tidak tersedia pada dataset"
            if internal
            else "Jam mendatang / belum rilis"
        )

    with st.container(border=True, key="forecast_summary"):
        forecast_status = (
            get_comparison_status(predicted_next, observed_next)
            if actual_next is not None
            else None
        )

        # Baris 1: Perbandingan Prediksi (t+1) vs Aktual (t+1)
        top1, top2 = st.columns(2, gap="medium")
        with top1:
            render_metric_card(
                label="🔮 Prediksi Cuaca (t+1)",
                value=predicted_next,
                footer="Model XGBoost",
                accent="teal",
                status=forecast_status,
            )
        with top2:
            render_metric_card(
                label=actual_card_label,
                value=observed_next,
                footer=actual_footer,
                accent="slate",
            )

        st.write("")

        # Baris 2: Target Waktu, Fenomena Basis (t), & Tingkat Kepercayaan
        c1, c2, c3 = st.columns([1.35, 1.35, 1.0], gap="medium")
        with c1:
            render_metric_card(
                label="🕒 Target Prediksi (t+1)",
                value=target_local.strftime("%H:%M"),
                footer=f"📅 {target_local.strftime('%d-%m-%Y')} • Basis {base_local.strftime('%H:%M')}",
                accent="navy",
            )
        with c2:
            render_metric_card(
                label="🌦️ Fenomena Saat Ini (t)",
                value=current_phenomenon,
                footer=obs_footer_t,
                accent="slate",
            )
        with c3:
            render_metric_card(
                label="🎯 Kepercayaan",
                value=f"{confidence_next:.2%}",
                footer="Probabilitas tertinggi",
                accent="teal",
            )

        st.write("")

        if actual_next is None:
            if internal:
                st.info("Data observasi aktual pada jam target (t+1) tidak tersedia di dalam file dataset ini.")
            else:
                st.info("Data observasi aktual pada jam target (t+1) belum tersedia di SYNOP (jam mendatang atau belum rilis).")
        else:
            comp = compare_prediction(predicted_next, observed_next)
            if comp == "Sesuai":
                st.success("✅ **Sesuai** — Prediksi model sesuai dengan fenomena aktual pada jam target.")
            elif comp == "Berbeda":
                st.warning("⚠️ **Berbeda** — Prediksi model berbeda dengan fenomena aktual pada jam target.")
            else:
                st.info("ℹ️ Data aktual pada jam target tidak dapat dibandingkan.")

    return forecast_1h.get("probabilities")

def _render_recent_context_table(df, selected_utc, selected_tz, hours=6):
    st.divider()
    st.subheader(f"🕒 Konteks Observasi {hours} Jam Menjelang Prediksi")
    st.caption(
        f"Ringkasan unsur cuaca dan fenomena aktual selama {hours} jam "
        "hingga jam basis prediksi (t)."
    )

    end_time = pd.Timestamp(selected_utc)
    start_time = end_time - pd.Timedelta(hours=hours - 1)

    sub_df = df[
        (df["data_timestamp"] >= start_time)
        & (df["data_timestamp"] <= end_time)
    ].sort_values("data_timestamp")

    rows = []
    for _, row in sub_df.iterrows():
        ts_local = row["data_timestamp"].tz_convert(selected_tz)
        rows.append({
            "Waktu": ts_local.strftime("%d-%m-%Y %H:%M"),
            "Fenomena Aktual (WW)": get_observed_phenomenon(row),
            "Visibility (km)": row.get("visibility_vv"),
            "Suhu (°C)": row.get("temp_drybulb_c_tttttt"),
            "RH (%)": row.get("relative_humidity_pc"),
            "Angin (kt)": row.get("wind_speed_ff"),
        })

    context_df = pd.DataFrame(rows)
    context_df.attrs = {}

    with st.container(border=True, key="forecast_context_card"):
        if context_df.empty:
            st.info("Data konteks observasi tidak tersedia.")
        else:
            st.dataframe(
                context_df,
                width="stretch",
                hide_index=True,
            )

def display_forecast_results(
    df,
    selected_datetime_iso,
    selected_timezone_label,
    timezones,
):
    """Tampilan khusus mode Prediksi Fenomena Cuaca 1 Jam ke Depan (t+1)."""
    if df is None or df.empty:
        st.warning("Data hasil pengamatan tidak tersedia.")
        return

    forecast_1h = df.attrs.get("forecast_1h") if hasattr(df, "attrs") else None
    ctx = prepare_observation_context(
        df=df,
        selected_datetime_iso=selected_datetime_iso,
        selected_timezone_label=selected_timezone_label,
        timezones=timezones,
    )

    fc_probs = _render_forecast_summary(forecast_1h)

    display_probability_chart(
        probabilities=fc_probs,
        title="📊 Probabilitas Setiap Kelas (Prediksi t+1)",
        caption="Tingkat probabilitas model XGBoost untuk setiap kelas fenomena pada 1 jam ke depan.",
        color=FORECAST_CHART_COLOR,
        key_suffix="t1",
    )

    param_caption = (
        "Kondisi parameter meteorologi pada jam basis (t) dari dataset internal."
        if is_internal_source(ctx["df"])
        else "Kondisi parameter meteorologi hasil decoding sandi SYNOP pada jam basis (t)."
    )
    display_meteorological_parameters(ctx["selected_data"], caption=param_caption)

    _render_recent_context_table(
        df=ctx["df"],
        selected_utc=ctx["selected_utc"],
        selected_tz=ctx["selected_tz"],
        hours=6,
    )

    display_visibility_chart(
        df=ctx["df"],
        selected_utc=ctx["selected_utc"],
        selected_tz=ctx["selected_tz"],
        selected_duration=6,
    )

    display_raw_and_export(
        df=ctx["df"],
        selected_data=ctx["selected_data"],
        selected_utc=ctx["selected_utc"],
        selected_tz=ctx["selected_tz"],
        key_prefix="forecast",
        forecast_1h=forecast_1h,
    )
import streamlit as st

NAVY = "#14324F"
TEAL = "#1F6F78"
BG = "#EEF2F5"
CARD = "#FFFFFF"
CONTROL_BG = "#E3EAF0"
BORDER = "#D3DCE4"
TEXT = "#1F2D3D"
MUTED = "#5B6B7B"


def apply_custom_style():
    st.markdown(
        f"""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap');

        /* =================================
           GLOBAL
        ================================= */
        html, body, .stApp, .stMarkdown, p, label, input, button, textarea,
        h1, h2, h3, h4 {{
            font-family: 'Plus Jakarta Sans', 'Segoe UI', sans-serif;
        }}
        .stApp {{
            background-color: {BG};
            color: {TEXT};
        }}
        [data-testid="stHeader"] {{
            background: transparent;
        }}
        footer {{
            visibility: hidden;
        }}
        .block-container {{
            padding-top: 3.2rem;
            padding-bottom: 2.5rem;
            max-width: 1200px;
        }}

        /* =================================
           HEADER UTAMA
        ================================= */
        .main-header {{
            background:
                radial-gradient(circle at 88% 18%, rgba(255,255,255,0.10), transparent 40%),
                linear-gradient(125deg, {NAVY} 0%, #1E5470 60%, #2A7480 100%);
            padding: 32px 36px;
            border-radius: 20px;
            margin-bottom: 12px;
            box-shadow: 0 8px 24px rgba(20, 50, 79, 0.14);
        }}
        .main-header h1 {{
            color: #FFFFFF !important;
            font-size: 2rem !important;
            font-weight: 800 !important;
            line-height: 1.2 !important;
            letter-spacing: -0.01em;
            margin: 0 0 8px 0 !important;
            padding: 0 !important;
        }}
        .main-header p {{
            color: #CFDCE6 !important;
            font-size: 0.95rem;
            line-height: 1.55;
            max-width: 680px;
            margin: 0 !important;
        }}
        .main-header .chips {{
            margin-top: 16px;
        }}
        .main-header .chip {{
            display: inline-block;
            padding: 4px 12px;
            margin: 0 8px 4px 0;
            border-radius: 999px;
            background: rgba(255, 255, 255, 0.14);
            border: 1px solid rgba(255, 255, 255, 0.25);
            color: #FFFFFF;
            font-size: 12px;
            font-weight: 600;
        }}
        .header-eyebrow {{
            display: inline-block;
            font-size: 0.78rem;
            font-weight: 700;
            letter-spacing: 0.08em;
            text-transform: uppercase;
            color: rgba(255, 255, 255, 0.88);
            background: rgba(255, 255, 255, 0.14);
            border: 1px solid rgba(255, 255, 255, 0.22);
            padding: 4px 12px;
            border-radius: 999px;
            margin-bottom: 10px;
        }}
        .main-header h1 {{
            margin-top: 2px !important;
            margin-bottom: 8px !important;
            letter-spacing: -0.01em;
        }}
        .main-header p {{
            max-width: 720px;
            line-height: 1.55;
            opacity: 0.92;
        }}

        /* =================================
           JUDUL SECTION
        ================================= */
        h2, h3, h4 {{
            color: {NAVY} !important;
            font-weight: 700 !important;
            letter-spacing: -0.005em;
        }}
        [data-testid="stCaptionContainer"] {{
            color: {MUTED} !important;
        }}

        /* =================================
           HALAMAN AWAL: 2 BOX MODE UTAMA
        ================================= */
        .st-key-mode_card_forecast,
        .st-key-mode_card_classification,
        .st-key-source_card_synop,
        .st-key-source_card_internal {{
            background-color: {CARD} !important;
            border: 1.5px solid {BORDER} !important;
            border-radius: 22px !important;
            padding: 34px 32px 30px 32px !important;
            box-shadow: 0 6px 20px rgba(20, 50, 79, 0.06);
            transition: transform 0.18s ease, box-shadow 0.18s ease, border-color 0.18s ease;
        }}
        .st-key-mode_card_forecast:hover,
        .st-key-source_card_synop:hover {{
            transform: translateY(-3px);
            border-color: {NAVY} !important;
            box-shadow: 0 12px 28px rgba(20, 50, 79, 0.11);
        }}
        .st-key-mode_card_classification:hover,
        .st-key-source_card_internal:hover {{
            transform: translateY(-3px);
            border-color: {TEAL} !important;
            box-shadow: 0 12px 28px rgba(31, 111, 120, 0.12);
        }}

        .mode-card-body {{
            text-align: center;
            padding: 6px 12px 18px 12px;
        }}
        .mode-icon-box {{
            width: 76px;
            height: 76px;
            border-radius: 20px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 2.35rem;
            margin: 0 auto 20px auto;
        }}
        .forecast-icon {{
            background: linear-gradient(135deg, #E4ECF4 0%, #D3E0EE 100%);
            border: 1px solid #C2D3E5;
        }}
        .class-icon {{
            background: linear-gradient(135deg, #DFF0F2 0%, #CBE5E8 100%);
            border: 1px solid #B6DCE0;
        }}
        .mode-title {{
            color: {NAVY};
            font-size: 1.85rem;
            font-weight: 800;
            letter-spacing: -0.02em;
            line-height: 1.2;
            margin-bottom: 10px;
        }}
        .mode-subtitle {{
            color: {MUTED};
            font-size: 0.95rem;
            line-height: 1.55;
            max-width: 310px;
            margin: 0 auto 18px auto;
        }}
        .mode-pill {{
            display: inline-block;
            padding: 5px 14px;
            border-radius: 999px;
            font-size: 12px;
            font-weight: 700;
            letter-spacing: 0.02em;
        }}
        .forecast-pill {{
            background-color: #E8EFF6;
            color: {NAVY};
        }}
        .class-pill {{
            background-color: #E2F2F3;
            color: {TEAL};
        }}

        /* =================================
           KARTU KONTROL & HASIL
        ================================= */
        .st-key-active_mode_bar {{
            background-color: {CARD} !important;
            border: 1px solid {BORDER} !important;
            border-radius: 16px !important;
            padding: 16px 24px !important;
            box-shadow: 0 2px 10px rgba(20, 50, 79, 0.04);
        }}

        .st-key-time_settings,
        .st-key-display_settings {{
            background-color: {CONTROL_BG} !important;
            border: 1px solid {BORDER} !important;
            border-radius: 18px !important;
            padding: 22px 26px !important;
        }}

        .st-key-prediction_summary,
        .st-key-forecast_summary,
        .st-key-probability_chart_t,
        .st-key-probability_chart_t1,
        .st-key-visibility_card,
        .st-key-temperature_card,
        .st-key-wind_pressure_card,
        .st-key-cloud_card,
        .st-key-timeline_card,
        .st-key-forecast_context_card,
        .st-key-visibility_graph_chart {{
            background-color: {CARD} !important;
            border: 1px solid {BORDER} !important;
            border-radius: 16px !important;
            padding: 20px 22px !important;
            box-shadow: 0 1px 2px rgba(20, 50, 79, 0.04),
                        0 4px 14px rgba(20, 50, 79, 0.05);
        }}

        /* Aksen tepi atas tiap kartu */
        .st-key-prediction_summary {{
            border-top: 3px solid {TEAL} !important;
            padding: 26px 28px !important;
            overflow: visible !important;
        }}
        .st-key-forecast_summary {{
            border-top: 3px solid {NAVY} !important;
            padding: 26px 28px !important;
            overflow: visible !important;
        }}
        .st-key-time_settings {{
            padding: 24px 28px 32px 28px !important;
        }}
        .st-key-visibility_card    {{ border-top: 3px solid {TEAL} !important; }}
        .st-key-temperature_card   {{ border-top: 3px solid #C98A4B !important; }}
        .st-key-wind_pressure_card {{ border-top: 3px solid #5C84AD !important; }}
        .st-key-cloud_card         {{ border-top: 3px solid #8E9EAE !important; }}

        /* =================================
           METRIC
        ================================= */
        [data-testid="stMetric"] {{
            background-color: #F4F7FA;
            border: 1px solid #E2E8ED;
            padding: 14px 16px;
            border-radius: 12px;
            overflow: hidden;
        }}
        .st-key-time_settings [data-testid="stMetric"],
        .st-key-display_settings [data-testid="stMetric"] {{
            background-color: #FFFFFF;
        }}
        [data-testid="stMetricLabel"] {{
            color: {MUTED};
            font-weight: 600;
        }}
        [data-testid="stMetricLabel"] p {{
            font-size: 0.85rem;
        }}
        [data-testid="stMetricValue"] {{
            color: {TEAL};
            font-weight: 800;
            font-size: 1.65rem;
            font-variant-numeric: tabular-nums;
        }}
        [data-testid="stMetricValue"],
        [data-testid="stMetricValue"] div,
        [data-testid="stMetricLabel"],
        [data-testid="stMetricLabel"] div,
        [data-testid="stMetricLabel"] p {{
            white-space: normal !important;
            overflow: visible !important;
            text-overflow: clip !important;
            overflow-wrap: anywhere;
            line-height: 1.25;
        }}
        .st-key-prediction_summary [data-testid="stMetricValue"],
        .st-key-forecast_summary [data-testid="stMetricValue"] {{
            font-size: 1.35rem;
        }}

        /* Kartu metrik kustom dengan aksen bawah */
        .custom-metric-card {{
            position: relative;
            background-color: #F7FAFC;
            border: 1px solid {BORDER};
            border-radius: 14px;
            overflow: visible;
            display: flex;
            flex-direction: column;
            justify-content: space-between;
            min-height: 148px;
            height: 100%;
        }}
        .custom-metric-card.card-match {{
            border-color: #2E8B57;
            background-color: #F3FAF6;
        }}
        .custom-metric-card.card-mismatch {{
            border-color: #D97706;
            background-color: #FFFBF2;
        }}
        .metric-status-badge {{
            position: absolute;
            top: -13px;
            right: -10px;
            width: 34px;
            height: 34px;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 1.05rem;
            font-weight: 900;
            color: #FFFFFF;
            border: 3px solid #FFFFFF;
            box-shadow: 0 4px 12px rgba(20, 50, 79, 0.24);
            z-index: 10;
        }}
        .badge-match {{
            background: linear-gradient(135deg, #1E8E5A, #28A76B);
        }}
        .badge-mismatch {{
            background: linear-gradient(135deg, #D97706, #F59E0B);
        }}
        .custom-metric-body {{
            padding: 18px 20px 14px 20px;
        }}
        .custom-metric-label {{
            color: {MUTED};
            font-size: 0.95rem;
            font-weight: 600;
            margin-bottom: 8px;
        }}
        .custom-metric-value {{
            color: {NAVY};
            font-size: 1.62rem;
            font-weight: 800;
            line-height: 1.25;
            word-break: break-word;
        }}
        .custom-metric-footer {{
            padding: 8px 18px;
            font-size: 0.88rem;
            font-weight: 600;
            color: #FFFFFF;
            letter-spacing: 0.01em;
            border-bottom-left-radius: 13px;
            border-bottom-right-radius: 13px;
        }}
        .accent-navy  {{ background-color: {NAVY}; }}
        .accent-teal  {{ background-color: {TEAL}; }}
        .accent-slate {{ background-color: #3E5871; }}

        /* =================================
           TOMBOL
        ================================= */
        .stButton > button {{
            border-radius: 12px;
            font-weight: 700;
            min-height: 46px;
            transition: background 0.2s ease, box-shadow 0.2s ease,
                        border-color 0.2s ease;
        }}
        .stButton > button[kind="primary"],
        .stButton > button[data-testid="stBaseButton-primary"] {{
            background: linear-gradient(100deg, {TEAL}, #2B8A8F);
            color: #FFFFFF;
            border: none;
            box-shadow: 0 4px 12px rgba(31, 111, 120, 0.22);
        }}
        .stButton > button[kind="primary"] p,
        .stButton > button[data-testid="stBaseButton-primary"] p {{
            color: #FFFFFF;
        }}
        .stButton > button[kind="primary"]:hover,
        .stButton > button[data-testid="stBaseButton-primary"]:hover {{
            background: {NAVY};
            color: #FFFFFF;
            border: none;
        }}
        .stButton > button[kind="secondary"],
        .stButton > button[data-testid="stBaseButton-secondary"] {{
            background: #FFFFFF;
            color: {TEAL};
            border: 1.5px solid {TEAL};
        }}
        .stButton > button[kind="secondary"] p,
        .stButton > button[data-testid="stBaseButton-secondary"] p {{
            color: {TEAL};
        }}
        .stButton > button[kind="secondary"]:hover,
        .stButton > button[data-testid="stBaseButton-secondary"]:hover {{
            background: {TEAL};
            border-color: {TEAL};
        }}
        .stButton > button[kind="secondary"]:hover p,
        .stButton > button[data-testid="stBaseButton-secondary"]:hover p {{
            color: #FFFFFF;
        }}
        .stButton > button:disabled {{
            background: #D9E0E6 !important;
            border: none !important;
            box-shadow: none !important;
            cursor: not-allowed;
        }}
        .stButton > button:disabled p {{
            color: #7B8DA0 !important;
        }}

        /* =================================
           INPUT, ALERT, DATAFRAME, EXPANDER
        ================================= */
        [data-testid="stWidgetLabel"] p {{
            color: {TEXT};
            font-weight: 600;
            font-size: 0.9rem;
        }}
        div[data-baseweb="select"] > div,
        div[data-baseweb="input"],
        div[data-baseweb="base-input"] {{
            background-color: #FFFFFF;
            border-radius: 10px;
            border-color: #C3CFDA;
        }}
        div[data-baseweb="select"] > div:focus-within,
        div[data-baseweb="input"]:focus-within {{
            border-color: {TEAL};
            box-shadow: 0 0 0 2px rgba(31, 111, 120, 0.18);
        }}
        [data-testid="stAlert"] {{
            border-radius: 12px;
            border: 1px solid {BORDER};
        }}
        [data-testid="stDataFrame"] {{
            border: 1px solid {BORDER};
            border-radius: 12px;
            overflow: hidden;
        }}
        [data-testid="stExpander"] {{
            background: #FFFFFF;
            border: 1px solid {BORDER};
            border-radius: 14px;
        }}

        /* Samakan tinggi kartu grid parameter */
        .st-key-visibility_card,
        .st-key-temperature_card,
        .st-key-wind_pressure_card,
        .st-key-cloud_card {{
            min-height: 195px;
        }}

        hr {{
            border-color: {BORDER};
            margin: 1.25rem 0;
        }}

        .custom-footer {{
            text-align: center;
            color: {MUTED};
            font-size: 12px;
            line-height: 1.7;
            padding: 14px 0 4px 0;
        }}

        /* =================================
           RESPONSIF (LAYAR KECIL)
        ================================= */
        @media (max-width: 640px) {{
            .block-container {{
                padding-top: 3.2rem;
                padding-bottom: 2.5rem;
                max-width: 1360px;
            }}
            .main-header {{
                padding: 24px 20px;
                border-radius: 16px;
            }}
            .main-header h1 {{
                font-size: 1.5rem !important;
            }}
            .st-key-mode_card_forecast,
            .st-key-mode_card_classification {{
                padding: 24px 20px !important;
            }}
            .mode-title {{
                font-size: 1.55rem;
            }}
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )
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
            /* padding atas lebih besar supaya tidak tertutup header Streamlit */
            padding-top: 3.5rem;
            padding-bottom: 2.5rem;
            max-width: 1280px;
        }}

        /* =================================
           HEADER UTAMA
        ================================= */
        .main-header {{
            background:
                radial-gradient(circle at 88% 18%, rgba(255,255,255,0.10), transparent 40%),
                linear-gradient(125deg, {NAVY} 0%, #1E5470 60%, #2A7480 100%);
            padding: 34px 36px;
            border-radius: 20px;
            margin-bottom: 8px;
            box-shadow: 0 8px 24px rgba(20, 50, 79, 0.14);
        }}
        .main-header h1 {{
            color: #FFFFFF !important;
            font-size: 2rem !important;
            font-weight: 800 !important;
            line-height: 1.2 !important;
            letter-spacing: -0.01em;
            margin: 0 0 10px 0 !important;
            padding: 0 !important;
        }}
        .main-header p {{
            color: #CFDCE6 !important;
            font-size: 0.95rem;
            line-height: 1.6;
            max-width: 720px;
            margin: 0 !important;
        }}
        .main-header .chips {{
            margin-top: 18px;
        }}
        .main-header .chip {{
            display: inline-block;
            padding: 4px 12px;
            margin: 0 8px 6px 0;
            border-radius: 999px;
            background: rgba(255, 255, 255, 0.14);
            border: 1px solid rgba(255, 255, 255, 0.25);
            color: #FFFFFF;
            font-size: 12px;
            font-weight: 600;
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
           KARTU / CONTAINER
           - Kartu input  : biru muda
           - Kartu hasil  : putih
        ================================= */
        .st-key-time_settings,
        .st-key-display_settings {{
            background-color: {CONTROL_BG} !important;
            border: 1px solid {BORDER} !important;
            border-radius: 16px !important;
        }}

        .st-key-prediction_summary,
        .st-key-probability_chart,
        .st-key-visibility_card,
        .st-key-temperature_card,
        .st-key-wind_pressure_card,
        .st-key-cloud_card,
        .st-key-timeline_card,
        .st-key-visibility_chart,
        .st-key-visibility_graph_chart {{
            background-color: {CARD} !important;
            border: 1px solid {BORDER} !important;
            border-radius: 16px !important;
            box-shadow: 0 1px 2px rgba(20, 50, 79, 0.04),
                        0 4px 14px rgba(20, 50, 79, 0.05);
        }}

        /* Aksen warna tipis di tepi atas tiap kartu parameter */
        .st-key-visibility_card   {{ border-top: 3px solid {TEAL} !important; }}
        .st-key-temperature_card  {{ border-top: 3px solid #C98A4B !important; }}
        .st-key-wind_pressure_card{{ border-top: 3px solid #5C84AD !important; }}
        .st-key-cloud_card        {{ border-top: 3px solid #8E9EAE !important; }}

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
        /* di dalam kartu input, metric tetap putih agar kontras */
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
            font-size: 1.7rem;
            font-variant-numeric: tabular-nums;
        }}
        [data-testid="stMetricValue"] > div {{
            white-space: normal;      /* teks panjang tidak terpotong "..." */
            overflow-wrap: anywhere;
        }}

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
        /* Tombol utama (Tampilkan Data dan Hasil) */
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
        /* Tombol sekunder (Gunakan Waktu Ini, dll.) */
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
           INPUT
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

        /* Radio horizontal dibuat seperti pilihan segmen */
        div[role="radiogroup"] {{
            gap: 0.5rem 1.25rem;
        }}

        /* =================================
           TABS (kalau dipakai di display_handler)
        ================================= */
        .stTabs [data-baseweb="tab-list"] {{
            gap: 6px;
            border-bottom: 1px solid {BORDER};
        }}
        .stTabs [data-baseweb="tab"] {{
            font-weight: 600;
            color: {MUTED};
            padding: 8px 16px;
        }}
        .stTabs [aria-selected="true"] {{
            color: {TEAL};
        }}
        .stTabs [data-baseweb="tab-highlight"] {{
            background-color: {TEAL};
        }}

        /* =================================
           ALERT (info / success / error)
        ================================= */
        [data-testid="stAlert"] {{
            border-radius: 12px;
            border: 1px solid {BORDER};
        }}

        /* =================================
           DATAFRAME & EXPANDER
        ================================= */
        [data-testid="stDataFrame"] {{
            border: 1px solid {BORDER};
            border-radius: 12px;
            overflow: hidden;
        }}
        [data-testid="stExpander"] {{
            background: #FFFFFF;
            border: 1px solid {BORDER};
            border-radius: 12px;
        }}
        /* =================================
           PENYESUAIAN KARTU HASIL
        ================================= */
        /* Samakan tinggi kartu yang berdampingan di grid parameter */
        .st-key-visibility_card,
        .st-key-temperature_card {{
            min-height: 190px;
        }}
        .st-key-wind_pressure_card,
        .st-key-cloud_card {{
            min-height: 190px;
        }}

        /* Teks fenomena di kartu prediksi lebih kecil agar tidak terlalu besar */
        .st-key-prediction_summary [data-testid="stMetricValue"] {{
            font-size: 1.35rem;
        }}

        /* =================================
           DIVIDER
        ================================= */
        hr {{
            border-color: {BORDER};
            margin: 1.25rem 0;
        }}

        /* =================================
           FOOTER
        ================================= */
        .custom-footer {{
            text-align: center;
            color: {MUTED};
            font-size: 12px;
            line-height: 1.7;
            padding: 14px 0 4px 0;
        }}

        /* =================================
           RESPONSIF (HP / layar kecil)
        ================================= */
        @media (max-width: 640px) {{
            .block-container {{
                padding-left: 1rem;
                padding-right: 1rem;
                padding-top: 3rem;
            }}
            .main-header {{
                padding: 24px 20px;
                border-radius: 16px;
            }}
            .main-header h1 {{
                font-size: 1.5rem !important;
            }}
            [data-testid="stMetricValue"] {{
                font-size: 1.4rem;
            }}
        }}
        </style>
        """,
        unsafe_allow_html=True
    )

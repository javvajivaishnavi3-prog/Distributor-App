import io
import os
import re
import sys
import pandas as pd
import streamlit as st

# Page Configuration
st.set_page_config(
    page_title="Vendor & Distributor Parts Lookup",
    page_icon="📦",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom Styling
st.markdown(
    """
    <style>
    .stApp {
        background: linear-gradient(135deg, #f8fafc 0%, #e2e8f0 100%);
    }

    .main-header {
        background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
        padding: 24px 30px;
        border-radius: 14px;
        color: white;
        margin-bottom: 25px;
        box-shadow: 0 4px 18px rgba(0, 0, 0, 0.08);
        border: 1px solid #334155;
    }
    .main-header h1 {
        color: #ffffff !important;
        margin: 0;
        font-weight: 800;
        font-size: 2.2rem;
        letter-spacing: -0.5px;
    }
    .main-header p {
        color: #94a3b8;
        margin-top: 6px;
        margin-bottom: 0;
        font-size: 1rem;
    }

    div[data-testid="stTextInput"] input {
        background-color: #ffffff !important;
        color: #0f172a !important;
        border: 1px solid #cbd5e1 !important;
        border-radius: 8px !important;
    }
    div[data-testid="stTextInput"] input:focus {
        border-color: #dc2626 !important;
        box-shadow: 0 0 0 1px #dc2626 !important;
    }

    .filter-card-red {
        background: #ffffff;
        padding: 14px 12px;
        border-radius: 10px;
        box-shadow: 0 4px 12px rgba(185, 28, 28, 0.06);
        border-top: 4px solid #dc2626;
        margin-bottom: 10px;
    }

    .filter-title-red {
        font-weight: 700;
        font-size: 0.8rem;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        margin-bottom: 6px;
        color: #991b1b;
    }

    span[data-baseweb="tag"] {
        background-color: #fee2e2 !important;
        border: 1px solid #fca5a5 !important;
        border-radius: 6px !important;
    }
    span[data-baseweb="tag"] span {
        color: #991b1b !important;
        font-weight: 600;
    }

    .result-card {
        background: #ffffff;
        border-left: 5px solid #dc2626;
        padding: 14px 20px;
        border-radius: 10px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.06);
    }

    .stDownloadButton > button {
        background: linear-gradient(135deg, #dc2626 0%, #b91c1c 100%) !important;
        color: white !important;
        border: none !important;
        font-weight: 700 !important;
        border-radius: 8px !important;
        padding: 8px 20px !important;
        box-shadow: 0 4px 12px rgba(220, 38, 38, 0.3) !important;
        transition: all 0.3s ease !important;
    }
    .stDownloadButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 16px rgba(220, 38, 38, 0.4) !important;
    }
    </style>
""",
    unsafe_allow_html=True,
)

# Application Header
st.markdown(
    """
    <div class="main-header">
        <h1>📦 Automotive Vendor & Parts Catalog</h1>
        <p>Stateless Real-Time Parts & Distributor Data Engine.</p>
    </div>
""",
    unsafe_allow_html=True,
)

# Base directory relative resolution for Streamlit Cloud
BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def clean_key(val):
    if not val or pd.isna(val):
        return ""
    return re.sub(r"[^a-z0-9]", "", str(val).lower())

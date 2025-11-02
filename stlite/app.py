import streamlit as st

# Import utility functions and page handlers
from utils import load_and_prepare_data
from page_handlers import render_top_page, render_lap_details_page

# -----------------------------
# App Configuration
# -----------------------------

st.set_page_config(page_title="delta-telemetry-viewer", layout="wide")

# Add logo to sidebar
st.logo("assets/logo.svg")

# -----------------------------
# Sidebar
# -----------------------------

with st.sidebar:
    # Navigation menu (using st.radio for stlite compatibility)
    st.subheader("ページ")
    selected = st.radio(
        "ナビゲーション",
        options=["Top", "Lap Details"],
        index=0,
        key="main_menu",
        label_visibility="collapsed"
    )

    st.divider()

    # CSV file upload
    st.header("CSV ファイルを選択")
    uploaded = st.file_uploader("CSV を選択", type=["csv"], key="csv_uploader")

    st.header("表示オプション")
    smooth = st.slider("移動平均(ポイント数)", min_value=1, max_value=21, value=1, step=2, key="smooth_slider")
    show_markers = st.checkbox("散布ポイントを表示", value=False, key="show_markers_checkbox")

# -----------------------------
# Load Data
# -----------------------------

# Note: In stlite (browser environment), we don't have access to local file system
# Users must upload a CSV file
df = load_and_prepare_data(uploaded, default_path=None)

if df is None:
    st.info("左のサイドバーからCSVファイルを選択してください。")
    st.stop()

# -----------------------------
# Render Selected Page
# -----------------------------

if selected == "Top":
    render_top_page(df, smooth, show_markers)
elif selected == "Lap Details":
    render_lap_details_page(df, smooth, show_markers)

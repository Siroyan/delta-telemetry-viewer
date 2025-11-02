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

    # CSV file selection
    st.header("データを選択")

    # Sample data selection
    # Note: Available sample files must be registered in index.html
    sample_files = {
        "なし": None,
        "emc_zenkoku_2025.csv": "data/emc_zenkoku_2025.csv",
    }

    selected_sample = st.selectbox(
        "サンプルデータ",
        options=list(sample_files.keys()),
        key="sample_selector"
    )

    # CSV file upload
    uploaded = st.file_uploader("または、CSVファイルをアップロード", type=["csv"], key="csv_uploader")

    st.header("表示オプション")
    smooth = st.slider("移動平均(ポイント数)", min_value=1, max_value=21, value=1, step=2, key="smooth_slider")
    show_markers = st.checkbox("散布ポイントを表示", value=False, key="show_markers_checkbox")

# -----------------------------
# Load Data
# -----------------------------

# Determine which data source to use
sample_path = sample_files.get(selected_sample)

# Priority: uploaded file > sample file
if uploaded is not None:
    df = load_and_prepare_data(uploaded, default_path=None)
elif sample_path is not None:
    # Load sample file from data/ folder
    df = load_and_prepare_data(None, default_path=sample_path)
else:
    df = None

if df is None:
    st.info("左のサイドバーからサンプルデータを選択するか、CSVファイルをアップロードしてください。")
    st.stop()

# -----------------------------
# Render Selected Page
# -----------------------------

if selected == "Top":
    render_top_page(df, smooth, show_markers)
elif selected == "Lap Details":
    render_lap_details_page(df, smooth, show_markers)

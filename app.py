import os
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px

# Import utility functions
from utils import load_csv, to_local_time


# -----------------------------
# App
# -----------------------------

st.set_page_config(page_title="Telemetry Viewer", layout="wide")
st.title("Telemetry CSV Viewer (Streamlit + Plotly)")

# Link to lap details page
st.info("📊 各ラップの詳細な分析を見るには、サイドバーから「Lap Details」ページに移動してください")

with st.sidebar:
    st.header("1) CSV ファイルを選択")
    uploaded = st.file_uploader("CSV を選択", type=["csv"])

    # Fallback to a default path (useful when running locally with a pre-provided file)
    default_path = os.environ.get("DEFAULT_CSV_PATH", "/mnt/data/output_flat.csv")
    use_default = False
    if uploaded is None and os.path.exists(default_path):
        use_default = st.toggle("サンプルCSVを使う (自動)", value=True)

    st.header("2) 表示オプション")
    smooth = st.slider("移動平均(ポイント数)", min_value=1, max_value=21, value=1, step=2)
    show_markers = st.checkbox("散布ポイントを表示", value=False)

# Load data
df = None
if uploaded is not None:
    df = load_csv(uploaded.getvalue())
elif use_default and os.path.exists(default_path):
    with open(default_path, "rb") as f:
        df = load_csv(f.read())

if df is None:
    st.info("左のサイドバーからCSVファイルを選択してください。")
    st.stop()

# Build derived columns
df = df.copy()
df["time_local"] = to_local_time(df, tz_name="Asia/Tokyo")
df = df.sort_values("timestamp_ms").reset_index(drop=True)

# Optional smoothing
if smooth and smooth > 1 and "speed" in df:
    df["speed_smooth"] = df["speed"].rolling(window=smooth, min_periods=1, center=True).mean()
    speed_col = "speed_smooth"
else:
    speed_col = "speed"

# Normalize distance per lap (reset to 0 at the start of each lap)
if "distance" in df and "lap_number" in df:
    df["distance_normalized"] = df.groupby("lap_number")["distance"].transform(lambda x: x - x.min())
else:
    if "distance" in df:
        df["distance_normalized"] = df["distance"]

# Lap filter
laps = sorted(df["lap_number"].dropna().unique().tolist()) if "lap_number" in df else [1]
with st.sidebar:
    sel_laps = st.multiselect("表示するラップ", laps, default=laps)

if "lap_number" in df:
    df_plot = df[df["lap_number"].isin(sel_laps)].copy()
else:
    df_plot = df.copy()
    df_plot["lap_number"] = 1

# -----------------------------
# Time vs Speed (Plotly)
# -----------------------------
st.subheader("時間 vs 速度 (ラップ別カラー)")
if "speed" not in df_plot:
    st.warning("このCSVには 'speed' 列が見つかりませんでした。列名を 'speed' にするか、'velocity' 等にしてください。")
else:
    line_mode = "lines+markers" if show_markers else "lines"
    fig_line = px.line(
        df_plot,
        x="time_local",
        y=speed_col,
        color=df_plot["lap_number"].astype(str) if "lap_number" in df_plot else None,
        labels={"time_local": "時刻", speed_col: "速度", "color": "ラップ"},
        markers=show_markers,
    )
    fig_line.update_traces(mode=line_mode)
    fig_line.update_layout(legend_title_text="ラップ", hovermode="x unified")
    st.plotly_chart(fig_line, use_container_width=True)

# -----------------------------
# Distance vs Speed (Plotly) - Multiple Charts
# -----------------------------
st.subheader("距離 vs 速度 (ラップ別カラー)")
if "distance_normalized" not in df_plot:
    st.warning("このCSVには 'distance' 列が見つかりませんでした。列名を 'distance' にするか、'dist' 等にしてください。")
elif "speed" not in df_plot:
    st.warning("このCSVには 'speed' 列が見つかりませんでした。列名を 'speed' にするか、'velocity' 等にしてください。")
else:
    line_mode = "lines+markers" if show_markers else "lines"

    # Define lap groups for each chart
    lap_groups = [
        {"title": "ラップ 1-2", "laps": [1, 2]},
        {"title": "ラップ 3-5", "laps": [3, 4, 5]},
        {"title": "ラップ 6-7", "laps": [6, 7]},
    ]

    for group in lap_groups:
        # Filter data for the specified laps
        df_group = df_plot[df_plot["lap_number"].isin(group["laps"])].copy()

        if not df_group.empty:
            st.markdown(f"### {group['title']}")
            fig_dist = px.line(
                df_group,
                x="distance_normalized",
                y=speed_col,
                color=df_group["lap_number"].astype(str),
                labels={"distance_normalized": "距離 (m)", speed_col: "速度", "color": "ラップ"},
                markers=show_markers,
            )
            fig_dist.update_traces(mode=line_mode)
            fig_dist.update_layout(
                legend_title_text="ラップ",
                hovermode="x unified",
                xaxis=dict(range=[0, 3000])
            )
            st.plotly_chart(fig_dist, use_container_width=True)
        else:
            st.info(f"{group['title']}: データがありません")

# -----------------------------
# Data preview
# -----------------------------
with st.expander("データの先頭を表示"):
    st.dataframe(df_plot.head(200))

st.caption("ヒント: 速度列は 'speed'、距離列は 'distance'、ラップ列は 'lap_number'、時刻は 'timestamp_ms' (UNIX epoch ms) を推奨。自動である程度の列名を推測します。")
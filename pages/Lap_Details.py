import os
import streamlit as st
import pandas as pd
import plotly.express as px

# Import utility functions from parent directory
import sys
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from utils import load_csv, to_local_time

st.set_page_config(page_title="ラップ詳細", layout="wide")
st.title("ラップ詳細表示")

# Sidebar: File upload and settings
with st.sidebar:
    st.header("1) CSV ファイルを選択")
    uploaded = st.file_uploader("CSV を選択", type=["csv"])

    # Fallback to a default path
    default_path = os.environ.get("DEFAULT_CSV_PATH", "/mnt/data/output_flat.csv")
    use_default = False
    if uploaded is None and os.path.exists(default_path):
        use_default = st.toggle("サンプルCSVを使う (自動)", value=True)

    st.header("2) 表示オプション")
    smooth = st.slider("移動平均(ポイント数)", min_value=1, max_value=21, value=1, step=2)
    show_markers = st.checkbox("散布ポイントを表示", value=False)

    st.header("3) 色の範囲設定")

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

# Normalize distance per lap
if "distance" in df and "lap_number" in df:
    df["distance_normalized"] = df.groupby("lap_number")["distance"].transform(lambda x: x - x.min())
else:
    if "distance" in df:
        df["distance_normalized"] = df["distance"]

# Speed range settings for color mapping
if "speed" in df:
    speed_min_default = float(df["speed"].min())
    speed_max_default = float(df["speed"].max())

    with st.sidebar:
        col_min, col_max = st.columns(2)
        with col_min:
            speed_color_min = st.number_input("最小速度", value=speed_min_default, step=1.0, format="%.1f")
        with col_max:
            speed_color_max = st.number_input("最大速度", value=speed_max_default, step=1.0, format="%.1f")
else:
    speed_color_min = None
    speed_color_max = None

# Get list of laps
laps = sorted(df["lap_number"].dropna().unique().tolist()) if "lap_number" in df else [1]

st.info(f"全 {len(laps)} ラップのデータを表示します")

# Display each lap
for lap_num in laps:
    st.divider()
    st.header(f"ラップ {lap_num}")

    # Filter data for this lap
    df_lap = df[df["lap_number"] == lap_num].copy()

    if df_lap.empty:
        st.warning(f"ラップ {lap_num} のデータが見つかりません。")
        continue

    # Check if necessary data exists
    has_map_data = "latitude" in df_lap and "longitude" in df_lap
    has_distance_data = "distance_normalized" in df_lap and "speed" in df_lap

    if not has_map_data and not has_distance_data:
        st.warning("地図データと距離データがありません。")
        continue

    # Create two columns for side-by-side display
    col1, col2 = st.columns(2)

    # Map column
    with col1:
        st.subheader("地図")
        if not has_map_data:
            st.warning("緯度・経度データがありません。")
        else:
            df_map_lap = df_lap.dropna(subset=["latitude", "longitude"]).copy()
            if df_map_lap.empty:
                st.info("緯度経度の有効な行がありません。")
            else:
                fig_map_lap = px.scatter_mapbox(
                    df_map_lap,
                    lat="latitude",
                    lon="longitude",
                    color="speed" if "speed" in df_map_lap else None,
                    color_continuous_scale="Turbo",
                    range_color=[speed_color_min, speed_color_max] if speed_color_min is not None and speed_color_max is not None else None,
                    hover_data={
                        "time_local": True,
                        "speed": True,
                        "latitude": ":.6f",
                        "longitude": ":.6f",
                    },
                    zoom=15,
                    height=500,
                )
                fig_map_lap.update_layout(
                    mapbox_style="open-street-map",
                    mapbox_bearing=60,
                    coloraxis_colorbar=dict(title="速度")
                )
                st.plotly_chart(fig_map_lap, use_container_width=True)

    # Distance vs speed chart column
    with col2:
        st.subheader("距離 vs 速度")
        if not has_distance_data:
            st.warning("距離または速度データがありません。")
        else:
            fig_dist_lap = px.scatter(
                df_lap,
                x="distance_normalized",
                y=speed_col,
                color="speed" if "speed" in df_lap else None,
                color_continuous_scale="Turbo",
                range_color=[speed_color_min, speed_color_max] if speed_color_min is not None and speed_color_max is not None else None,
                labels={"distance_normalized": "距離 (m)", speed_col: "速度"},
                hover_data={
                    "time_local": True,
                    "distance_normalized": ":.1f",
                    speed_col: ":.2f",
                }
            )

            # Add line trace if not showing markers
            if not show_markers:
                fig_dist_lap.add_scatter(
                    x=df_lap["distance_normalized"],
                    y=df_lap[speed_col],
                    mode="lines",
                    line=dict(color="gray", width=1),
                    showlegend=False,
                    hoverinfo="skip",
                )

            fig_dist_lap.update_layout(
                hovermode="closest",
                height=500,
                coloraxis_colorbar=dict(title="速度")
            )
            st.plotly_chart(fig_dist_lap, use_container_width=True)

st.caption("ヒント: 速度列は 'speed'、距離列は 'distance'、ラップ列は 'lap_number'、時刻は 'timestamp_ms' (UNIX epoch ms) を推奨。自動である程度の列名を推測します。")

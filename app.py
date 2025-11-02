import os
import io
import sys
from typing import Tuple, Optional

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px

# -----------------------------
# Helpers
# -----------------------------

def _infer_time_unit(series: pd.Series) -> str:
    """
    Infer if a numeric timestamp is in milliseconds or seconds.
    Returns 'ms' or 's' (defaults to 'ms').
    """
    try:
        s = pd.to_numeric(series, errors="coerce").dropna()
        if s.empty:
            return "ms"
        # Heuristic: UNIX epoch ms usually > 10^12 around year 2001+,
        # seconds < 10^10 for a long while.
        if s.median() > 1e11:
            return "ms"
        return "s"
    except Exception:
        return "ms"


def _standardize_columns(df: pd.DataFrame) -> pd.DataFrame:
    """
    Rename columns to a canonical set and coerce types.
    Canonical names:
      - timestamp_ms (int64)
      - speed (float)
      - lap_number (int)
      - latitude (float)
      - longitude (float)
      - distance (float)
      - average_speed (float, optional)
      - total_time_ms (int, optional)
      - lap_time_ms (int, optional)
    """
    # Lower-case col mapping for robust matching
    colmap = {c.lower(): c for c in df.columns}
    def has(*opts):
        for o in opts:
            if o in colmap:
                return colmap[o]
        return None

    # Build rename dict
    rename = {}
    # timestamp-like
    ts_col = has("timestamp_ms", "time_ms", "epoch_ms", "ts_ms", "timestamp")
    if ts_col is None:
        # Try generic "time"
        ts_col = has("time")
    if ts_col is not None:
        rename[ts_col] = "timestamp_raw"
    # speed-like
    sp_col = has("speed", "velocity", "v")
    if sp_col: rename[sp_col] = "speed"
    # lap-like
    lap_col = has("lap_number", "lap", "lapno", "lap_id")
    if lap_col: rename[lap_col] = "lap_number"
    # latitude/longitude
    lat_col = has("latitude", "lat")
    lon_col = has("longitude", "lon", "lng", "long")
    if lat_col: rename[lat_col] = "latitude"
    if lon_col: rename[lon_col] = "longitude"
    # distance-like
    dist_col = has("distance", "dist", "d")
    if dist_col: rename[dist_col] = "distance"
    # optional
    avg_sp_col = has("average_speed", "avg_speed", "mean_speed")
    if avg_sp_col: rename[avg_sp_col] = "average_speed"
    total_t_col = has("total_time_ms", "total_ms", "elapsed_ms")
    if total_t_col: rename[total_t_col] = "total_time_ms"
    lap_t_col = has("lap_time_ms", "lap_ms")
    if lap_t_col: rename[lap_t_col] = "lap_time_ms"

    if rename:
        df = df.rename(columns=rename)

    # Coerce types safely
    if "speed" in df:
        df["speed"] = pd.to_numeric(df["speed"], errors="coerce")

    if "lap_number" in df:
        df["lap_number"] = pd.to_numeric(df["lap_number"], errors="coerce").fillna(1).astype(int)
    else:
        df["lap_number"] = 1

    if "latitude" in df:
        df["latitude"] = pd.to_numeric(df["latitude"], errors="coerce")
    if "longitude" in df:
        df["longitude"] = pd.to_numeric(df["longitude"], errors="coerce")

    if "distance" in df:
        df["distance"] = pd.to_numeric(df["distance"], errors="coerce")

    for opt in ["average_speed", "total_time_ms", "lap_time_ms"]:
        if opt in df:
            df[opt] = pd.to_numeric(df[opt], errors="coerce")

    # Timestamp handling
    if "timestamp_raw" in df:
        # Determine if raw is numeric or ISO string
        # Try numeric first
        numeric = pd.to_numeric(df["timestamp_raw"], errors="coerce")
        if numeric.notna().sum() > 0:
            unit = _infer_time_unit(numeric)
            if unit == "s":
                numeric = (numeric * 1000.0)
            df["timestamp_ms"] = numeric.astype("Int64")
        else:
            # Try parse as datetime string
            dt = pd.to_datetime(df["timestamp_raw"], errors="coerce", utc=True)
            df["timestamp_ms"] = (dt.view("int64") // 1_000_000).astype("Int64")

    # If no timestamp available, synthesize an index-based time (0,1,2,... seconds)
    if "timestamp_ms" not in df:
        df["timestamp_ms"] = (pd.RangeIndex(len(df)) * 1000).astype("Int64")

    return df


@st.cache_data(show_spinner=False)
def load_csv(file_bytes: bytes) -> pd.DataFrame:
    df = pd.read_csv(io.BytesIO(file_bytes))
    df = _standardize_columns(df)
    # Drop rows without lat/lon if both missing (keep partial for line chart)
    if "latitude" in df and "longitude" in df:
        # nothing to do; keep NaNs for map filtering later
        pass
    return df


def to_local_time(df: pd.DataFrame, tz_name: str = "Asia/Tokyo") -> pd.Series:
    # Convert ms epoch to localized datetime
    # Treat values as UTC epoch unless otherwise stated
    ts = pd.to_datetime(df["timestamp_ms"], unit="ms", utc=True, errors="coerce")
    try:
        return ts.dt.tz_convert(tz_name)
    except Exception:
        return ts  # fallback UTC


# -----------------------------
# App
# -----------------------------

st.set_page_config(page_title="Telemetry Viewer", layout="wide")
st.title("Telemetry CSV Viewer (Streamlit + Plotly)")

with st.sidebar:
    st.header("1) CSV ファイルを選択")
    uploaded = st.file_uploader("CSV を選択", type=["csv"])

    # Fallback to a default path (useful when running locally with a pre-provided file)
    default_path = os.environ.get("DEFAULT_CSV_PATH", "/mnt/data/output_flat.csv")
    use_default = False
    if uploaded is None and os.path.exists(default_path):
        use_default = st.toggle("サンプルCSVを使う (自動)", value=True)
    tz = st.selectbox("タイムゾーン", ["Asia/Tokyo", "UTC", "Asia/Seoul", "America/Los_Angeles", "Europe/London"], index=0)

    st.header("2) 表示オプション")
    smooth = st.slider("移動平均(ポイント数)", min_value=1, max_value=21, value=1, step=2)
    show_markers = st.checkbox("散布ポイントを表示", value=False)

# Load data
df: Optional[pd.DataFrame] = None
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
df["time_local"] = to_local_time(df, tz_name=tz)
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

    st.header("3) ラップ詳細表示")
    detail_lap = st.selectbox("詳細を見るラップ", options=[None] + laps, format_func=lambda x: "選択なし" if x is None else f"ラップ {x}")
    show_detail = detail_lap is not None

    # Speed range settings for color mapping
    if show_detail and "speed" in df:
        st.subheader("色の範囲設定")
        speed_min_default = float(df["speed"].min())
        speed_max_default = float(df["speed"].max())

        col_min, col_max = st.columns(2)
        with col_min:
            speed_color_min = st.number_input("最小速度", value=speed_min_default, step=1.0, format="%.1f")
        with col_max:
            speed_color_max = st.number_input("最大速度", value=speed_max_default, step=1.0, format="%.1f")
    else:
        speed_color_min = None
        speed_color_max = None

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
# Map (Plotly Mapbox)
# -----------------------------
st.subheader("走行軌跡 (地図)")
if "latitude" not in df_plot or "longitude" not in df_plot:
    st.warning("このCSVには 'latitude' と 'longitude' 列が必要です。")
else:
    df_map = df_plot.dropna(subset=["latitude", "longitude"]).copy()
    if df_map.empty:
        st.info("緯度経度の有効な行がありません。")
    else:
        fig_map = px.scatter_mapbox(
            df_map,
            lat="latitude",
            lon="longitude",
            color=df_map["lap_number"].astype(str),
            hover_data={
                "time_local": True,
                "speed": True,
                "lap_number": True,
                "latitude": ":.6f",
                "longitude": ":.6f",
            },
            zoom=12,
            height=600,
        )
        # OpenStreetMap style doesn't need a token
        fig_map.update_layout(mapbox_style="open-street-map", legend_title_text="ラップ")
        st.plotly_chart(fig_map, use_container_width=True)

# -----------------------------
# Lap Detail View
# -----------------------------
if show_detail:
    st.divider()
    st.header(f"ラップ {detail_lap} の詳細")

    # Filter data for the selected lap
    df_detail = df[df["lap_number"] == detail_lap].copy()

    if df_detail.empty:
        st.warning(f"ラップ {detail_lap} のデータが見つかりません。")
    else:
        # Create two columns for side-by-side display
        col1, col2 = st.columns(2)

        with col1:
            st.subheader("地図")
            # Map for selected lap
            if "latitude" not in df_detail or "longitude" not in df_detail:
                st.warning("緯度・経度データがありません。")
            else:
                df_map_detail = df_detail.dropna(subset=["latitude", "longitude"]).copy()
                if df_map_detail.empty:
                    st.info("緯度経度の有効な行がありません。")
                else:
                    # Use speed for color gradient (slow = blue, fast = red)
                    fig_map_detail = px.scatter_mapbox(
                        df_map_detail,
                        lat="latitude",
                        lon="longitude",
                        color="speed" if "speed" in df_map_detail else None,
                        color_continuous_scale="Turbo",  # Blue (slow) to Red (fast)
                        range_color=[speed_color_min, speed_color_max] if speed_color_min is not None and speed_color_max is not None else None,
                        hover_data={
                            "time_local": True,
                            "speed": True,
                            "latitude": ":.6f",
                            "longitude": ":.6f",
                        },
                        zoom=14,
                        height=500,
                    )
                    fig_map_detail.update_layout(
                        mapbox_style="open-street-map",
                        coloraxis_colorbar=dict(title="速度")
                    )
                    st.plotly_chart(fig_map_detail, use_container_width=True)

        with col2:
            st.subheader("距離 vs 速度")
            # Distance vs speed chart for selected lap
            if "distance_normalized" not in df_detail:
                st.warning("距離データがありません。")
            elif "speed" not in df_detail:
                st.warning("速度データがありません。")
            else:
                # Use scatter plot with color gradient matching the map
                fig_dist_detail = px.scatter(
                    df_detail,
                    x="distance_normalized",
                    y=speed_col,
                    color="speed" if "speed" in df_detail else None,
                    color_continuous_scale="Turbo",  # Same scale as map: Blue (slow) to Red (fast)
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
                    # Add a line connecting the points
                    fig_dist_detail.add_scatter(
                        x=df_detail["distance_normalized"],
                        y=df_detail[speed_col],
                        mode="lines",
                        line=dict(color="gray", width=1),
                        showlegend=False,
                        hoverinfo="skip",
                    )

                fig_dist_detail.update_layout(
                    hovermode="closest",
                    height=500,
                    coloraxis_colorbar=dict(title="速度")
                )
                st.plotly_chart(fig_dist_detail, use_container_width=True)

# -----------------------------
# Data preview
# -----------------------------
with st.expander("データの先頭を表示"):
    st.dataframe(df_plot.head(200))

st.caption("ヒント: 速度列は 'speed'、距離列は 'distance'、ラップ列は 'lap_number'、時刻は 'timestamp_ms' (UNIX epoch ms) を推奨。自動である程度の列名を推測します。")
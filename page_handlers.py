import streamlit as st
import plotly.express as px
from utils import to_local_time


def render_top_page(df, smooth, show_markers):
    """Render the top page with overview charts."""
    st.title("Telemetry CSV Viewer (Streamlit + Plotly)")

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

    # Lap filter
    laps = sorted(df["lap_number"].dropna().unique().tolist()) if "lap_number" in df else [1]
    with st.sidebar:
        sel_laps = st.multiselect("表示するラップ", laps, default=laps, key="top_lap_filter")

    if "lap_number" in df:
        df_plot = df[df["lap_number"].isin(sel_laps)].copy()
    else:
        df_plot = df.copy()
        df_plot["lap_number"] = 1

    # Time vs Speed
    st.subheader("時間 vs 速度 (ラップ別カラー)")
    if "speed" not in df_plot:
        st.warning("このCSVには 'speed' 列が見つかりませんでした。")
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

    # Distance vs Speed - Multiple Charts
    st.subheader("距離 vs 速度 (ラップ別カラー)")
    if "distance_normalized" not in df_plot:
        st.warning("このCSVには 'distance' 列が見つかりませんでした。")
    elif "speed" not in df_plot:
        st.warning("このCSVには 'speed' 列が見つかりませんでした。")
    else:
        line_mode = "lines+markers" if show_markers else "lines"

        lap_groups = [
            {"title": "ラップ 1-2", "laps": [1, 2]},
            {"title": "ラップ 3-5", "laps": [3, 4, 5]},
            {"title": "ラップ 6-7", "laps": [6, 7]},
        ]

        for group in lap_groups:
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

    # Data preview
    with st.expander("データの先頭を表示"):
        st.dataframe(df_plot.head(200))

    st.caption("ヒント: 速度列は 'speed'、距離列は 'distance'、ラップ列は 'lap_number'、時刻は 'timestamp_ms' (UNIX epoch ms) を推奨。")


def render_lap_details_page(df, smooth, show_markers):
    """Render the lap details page with individual lap analysis."""
    st.title("ラップ詳細表示")

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

    # Speed range settings
    if "speed" in df:
        speed_min_default = float(df["speed"].min())
        speed_max_default = float(df["speed"].max())

        with st.sidebar:
            st.subheader("色の範囲設定")
            col_min, col_max = st.columns(2)
            with col_min:
                speed_color_min = st.number_input("最小速度", value=speed_min_default, step=1.0, format="%.1f", key="lap_speed_min")
            with col_max:
                speed_color_max = st.number_input("最大速度", value=speed_max_default, step=1.0, format="%.1f", key="lap_speed_max")
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

        df_lap = df[df["lap_number"] == lap_num].copy()

        if df_lap.empty:
            st.warning(f"ラップ {lap_num} のデータが見つかりません。")
            continue

        has_map_data = "latitude" in df_lap and "longitude" in df_lap
        has_distance_data = "distance_normalized" in df_lap and "speed" in df_lap

        if not has_map_data and not has_distance_data:
            st.warning("地図データと距離データがありません。")
            continue

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

    st.caption("ヒント: 速度列は 'speed'、距離列は 'distance'、ラップ列は 'lap_number'、時刻は 'timestamp_ms' (UNIX epoch ms) を推奨。")

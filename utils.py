import io
import pandas as pd
import streamlit as st


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

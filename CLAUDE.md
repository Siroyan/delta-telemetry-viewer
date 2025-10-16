# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Communication Language

**IMPORTANT**: Always respond in Japanese (日本語) when working in this repository. All explanations, comments, and communications with the user must be in Japanese.

## Project Overview

Delta Telemetry Viewer is a Streamlit web application for visualizing racing/vehicle telemetry data from CSV files. The application displays:
- Time-series speed charts with lap-based coloring
- GPS trajectory maps using Plotly Mapbox
- Interactive data filtering by lap number
- Time zone conversion and data smoothing

## Development Commands

### Running the Application
```bash
streamlit run app.py
```
The app will be available at `http://localhost:8501` (port 8501 is auto-forwarded in devcontainer).

### Installing Dependencies
```bash
pip install -r requirements.txt
```

## Architecture

### Single-File Application (app.py)
The entire application logic resides in `app.py` with the following structure:

**Helper Functions (Lines 15-144)**
- `_infer_time_unit()`: Auto-detects if timestamps are in milliseconds or seconds based on magnitude
- `_standardize_columns()`: Core data normalization function that maps various column naming conventions to canonical names:
  - Timestamp columns → `timestamp_ms` (always stored as milliseconds since epoch)
  - Speed/velocity columns → `speed`
  - Lap columns → `lap_number`
  - GPS columns → `latitude`, `longitude`
  - Optional columns: `average_speed`, `total_time_ms`, `lap_time_ms`
- `load_csv()`: Cached CSV loader with automatic column standardization
- `to_local_time()`: Converts UTC epoch timestamps to specified timezone

**Streamlit UI (Lines 150-259)**
- Sidebar: File upload, timezone selection, smoothing controls, lap filtering
- Main content: Speed vs time line chart, GPS trajectory map, data preview
- Default CSV fallback: Checks `DEFAULT_CSV_PATH` environment variable for `/mnt/data/output_flat.csv`

### Data Flow
1. CSV upload or default file load → `load_csv()`
2. Column name inference and standardization → `_standardize_columns()`
3. Timestamp conversion → `to_local_time()` based on selected timezone
4. Optional moving average smoothing on speed data
5. Lap-based filtering for visualization
6. Plotly chart generation (line chart + mapbox scatter)

### Expected CSV Format
The app is flexible with column names but expects data containing:
- **Required**: Timestamp column (numeric epoch or ISO string format)
- **Optional**: speed, lap_number, latitude, longitude
- Automatic inference handles variations like: `timestamp_ms`, `time`, `epoch_ms`, `velocity`, `v`, `lap`, `lat`, `lon`, etc.

### Technology Stack
- **Streamlit**: Web framework (v1.50.0)
- **Plotly**: Interactive charts (v6.3.1)
- **Pandas**: Data manipulation (v2.3.3)
- **NumPy**: Numerical operations (v2.3.4)

## Key Implementation Details

### Timestamp Handling (Lines 104-121)
- Attempts numeric parsing first (assumes UNIX epoch)
- Falls back to ISO datetime string parsing if numeric fails
- Auto-detects milliseconds vs seconds using median value heuristic (>10^11 = ms)
- Synthesizes sequential timestamps if none exist

### UI Language
The interface uses Japanese labels (`時間 vs 速度`, `走行軌跡`, etc.) for primary user-facing text.

### Caching
The `@st.cache_data` decorator on `load_csv()` prevents redundant file parsing when Streamlit reruns due to widget interactions.

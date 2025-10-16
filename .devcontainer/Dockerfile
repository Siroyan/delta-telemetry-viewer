FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl ca-certificates git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /workspaces/delta-telemetry-viewer

# ここで先に numpy/pyarrow を入れてホイール取得を確実化
RUN pip install -U pip wheel setuptools && \
    pip install "numpy>=2.2,<2.4" "pyarrow>=17,<19"
# あとは requirements.txt 側の依存を入れる（postCreateCommand で実行）

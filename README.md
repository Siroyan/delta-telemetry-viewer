# Delta Telemetry Viewer

レーシング・車両テレメトリーデータをビジュアライズするためのStreamlitベースのWebアプリケーションです。CSVファイルから速度、GPS位置、ラップ情報などのデータを読み込み、インタラクティブなグラフと地図で表示します。

## 主な機能

- **時系列速度グラフ**: ラップごとに色分けされた速度チャート
- **GPS軌跡マップ**: Plotly Mapboxを使用した走行軌跡の可視化
- **ラップフィルター**: 特定のラップのみを選択して表示
- **タイムゾーン変換**: UTC、JST、その他のタイムゾーンに対応
- **データスムージング**: 移動平均による速度データの平滑化
- **柔軟な列名対応**: 様々な列名規則を自動認識

## 必要環境

- Python 3.8以上
- 必要なパッケージは`requirements.txt`に記載

## インストール

```bash
# 依存パッケージのインストール
pip install -r requirements.txt
```

## 使い方

このアプリケーションは **Stlite（ブラウザ版Streamlit）** を使用して、サーバー不要で動作します。ブラウザ内でPythonが実行されるため、AWS S3やGitHub Pagesなどの静的ホスティングサービスで公開できます。

### ローカルでのテスト

```bash
python -m http.server 8502
```

ブラウザで `http://localhost:8502` にアクセスしてください。

**注意**: 初回読み込みには時間がかかります（Pythonランタイムとライブラリをダウンロードするため）。

### AWS S3へのデプロイ

1. S3バケットを作成し、静的Webサイトホスティングを有効化
2. プロジェクトルートの`index.html`、`app.py`、`utils.py`、`page_handlers.py`、`assets/`フォルダをS3バケットにアップロード
3. バケットのパブリックアクセス設定を調整（パブリック読み取りを許可）
4. S3のWebサイトエンドポイントにアクセス

### GitHub Pagesへのデプロイ

1. GitHubリポジトリの Settings > Pages を開く
2. Source を「Deploy from a branch」に設定
3. Branch を選択（通常は`main`）、フォルダを `/`（root）に設定
4. 数分後、`https://<username>.github.io/<repository>/` でアクセス可能

### 従来のStreamlitサーバーとして実行（非推奨）

従来のStreamlitサーバーとして実行する場合は、以下の変更が必要です：

1. `app.py`の49行目：`default_path=None` → `default_path=os.environ.get("DEFAULT_CSV_PATH")`を追加
2. ファイル先頭に`import os`を追加

```bash
streamlit run app.py
```

### CSVファイルの準備

アプリケーションは以下のデータ列を含むCSVファイルに対応しています：

#### 必須列
- **タイムスタンプ**: 以下のいずれかの形式
  - `timestamp_ms`, `time_ms`, `epoch_ms`, `timestamp`, `time`
  - UNIXエポック（ミリ秒または秒）または ISO 8601形式の文字列

#### オプション列
- **速度**: `speed`, `velocity`, `v`
- **ラップ番号**: `lap_number`, `lap`, `lapno`, `lap_id`
- **GPS座標**:
  - 緯度: `latitude`, `lat`
  - 経度: `longitude`, `lon`, `lng`, `long`
- **その他**: `average_speed`, `total_time_ms`, `lap_time_ms`

**注意**: 列名は大文字・小文字を区別しません。アプリケーションが自動的に認識します。

### CSVファイル例

```csv
timestamp_ms,speed,lap_number,latitude,longitude
1609459200000,45.5,1,35.6812,139.7671
1609459201000,52.3,1,35.6813,139.7672
1609459202000,58.1,1,35.6814,139.7673
```

### 使用手順

1. **CSVファイルのアップロード**: 左サイドバーの「CSV ファイルを選択」からファイルを選択
2. **ページ選択**: "Top"（全体ビュー）または"Lap Details"（ラップ詳細）を選択
3. **表示オプションの調整**:
   - 移動平均のウィンドウサイズを調整（1-21ポイント）
   - 散布ポイントの表示/非表示を切り替え
4. **データの確認**: グラフと地図でデータを可視化

**注意**: Stlite版ではブラウザ内でファイルを処理するため、アップロードしたCSVファイルはサーバーに送信されません（プライバシー保護）。

## 開発環境

このプロジェクトはDevcontainer対応です。VS Codeの「Reopen in Container」機能を使用することで、すぐに開発を開始できます。

### Devcontainer環境
- Python 3.12
- 自動的にポート8501が転送されます
- 必要な拡張機能が自動インストールされます

## 技術スタック

- **[Stlite](https://github.com/whitphx/stlite)** (@stlite/browser v0.89.1): ブラウザ内でStreamlit 1.48.0を実行（WebAssembly/Pyodide）
- **[Plotly](https://plotly.com/python/)** (v6.3.1): インタラクティブなグラフ作成
- **[Pandas](https://pandas.pydata.org/)** (v2.3.3): データ処理
- **[NumPy](https://numpy.org/)** (v2.3.4): 数値計算
- **[Pytz](https://pythonhosted.org/pytz/)** (v2025.2): タイムゾーン処理

**メリット:**
- サーバー不要（静的ホスティング可能）
- 低コスト運用（S3やGitHub Pagesで月数円〜無料）
- プライバシー保護（データがブラウザ外に出ない）
- オフライン動作可能（初回読み込み後）

## ライセンス

このプロジェクトはオープンソースです。

## トラブルシューティング

### CSVファイルが読み込めない
- 列名が正しいか確認してください（大文字・小文字は自動判定されます）
- タイムスタンプがUNIXエポック（ミリ秒または秒）またはISO 8601形式であることを確認してください

### 地図が表示されない
- `latitude`（緯度）と`longitude`（経度）列が存在することを確認してください
- 座標値が有効な範囲（緯度: -90〜90、経度: -180〜180）内であることを確認してください

### グラフが空白
- `speed`列が存在し、有効な数値データが含まれていることを確認してください
- 選択したラップにデータが存在することを確認してください

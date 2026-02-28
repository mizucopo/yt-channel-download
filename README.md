# YouTube Live Archive Downloader

YouTubeライブアーカイブ（VOD）を自動的に検出・ダウンロードし、スクリーンショットを抽出してGoogle Driveへアップロード、その後ローカルファイルを削除するシステム。

## 機能

- **自動検出**: 指定チャンネルのライブ配信アーカイブをYouTube APIで検出
- **ダウンロード**: yt-dlpを使用した高品質動画ダウンロード
- **サムネイル抽出**: ffmpegで指定間隔のスクリーンショットを抽出
- **Google Driveアップロード**: mizu-common-pyのGoogleDriveProviderを使用
- **自動クリーンアップ**: アップロード完了後のローカルファイル削除
- **中断回復**: 処理が中断されたストリームの自動回復

## 状態遷移

```
discovered → downloading → downloaded → thumbs_done → uploading → uploaded → cleaned
canceled (初回検出時のスキップ状態)
```

## 必要条件

**ローカル実行の場合:**
- Python 3.14+
- ffmpeg（サムネイル抽出用）
- Google OAuth認証情報

**Dockerの場合:**
- Docker
- Google OAuth認証情報

## インストール

```bash
# リポジトリをクローン
git clone https://github.com/mizucopo/yt-live-download.git
cd yt-live-download

# 依存関係をインストール
uv sync
```

## 設定

環境変数または`.env`ファイルで設定します。

> **初回セットアップ時**: Google OAuth 認証情報の取得方法は [docs/google_oauth_setup.md](docs/google_oauth_setup.md) を参照してください。

| 環境変数 | 説明 | デフォルト |
|---------|------|-----------|
| `YOUTUBE_CHANNEL_IDS` | 対象チャンネルID（カンマ区切り） | （必須） |
| `GOOGLE_OAUTH_CLIENT_ID` | Google OAuth クライアントID | （必須） |
| `GOOGLE_OAUTH_CLIENT_SECRET` | Google OAuth クライアントシークレット | `` |
| `GOOGLE_REFRESH_TOKEN` | Google OAuth リフレッシュトークン | （必須） |
| `GDRIVE_ROOT_FOLDER_ID` | Google DriveルートフォルダID | （必須） |
| `DATABASE_PATH` | データベースファイルパス | `data/streams.db` |
| `DOWNLOAD_DIR` | ダウンロードディレクトリ | `data/downloads` |
| `THUMBNAIL_DIR` | サムネイルディレクトリ | `data/thumbnails` |
| `THUMBNAIL_INTERVAL` | サムネイル抽出間隔（秒） | `60` |
| `MAX_RETRIES` | 最大リトライ回数 | `3` |
| `LOCK_STALE_HOURS` | ロックファイルの有効期限（時間） | `3` |

## 使用方法

### CLIコマンド

```bash
# 全パイプラインを実行（中断されたストリームの自動復旧を含む）
python -m src.main run

# ステータス確認
python -m src.main status

# ロックファイル削除
python -m src.main unlock

# Google OAuth認証
python -m src.main auth
```

### オプション

```bash
# 詳細ログを有効にする
python -m src.main -v run
```

## Docker

Dockerイメージを使用して実行できます。

```bash
# イメージを取得
docker pull mizucopo/yt-live-download

# ヘルプ表示
docker run --rm mizucopo/yt-live-download --help

# 全パイプラインを実行
docker run --rm \
  -e YOUTUBE_CHANNEL_IDS="channel_id1,channel_id2" \
  -e GOOGLE_OAUTH_CLIENT_ID="your_client_id" \
  -e GOOGLE_OAUTH_CLIENT_SECRET="your_client_secret" \
  -e GOOGLE_REFRESH_TOKEN="your_refresh_token" \
  -e GDRIVE_ROOT_FOLDER_ID="your_folder_id" \
  -v ./data:/app/data \
  mizucopo/yt-live-download run

# 詳細ログを有効にする
docker run --rm \
  -e YOUTUBE_CHANNEL_IDS="..." \
  -e GOOGLE_OAUTH_CLIENT_ID="..." \
  -e GOOGLE_OAUTH_CLIENT_SECRET="..." \
  -e GOOGLE_REFRESH_TOKEN="..." \
  -e GDRIVE_ROOT_FOLDER_ID="..." \
  -v ./data:/app/data \
  mizucopo/yt-live-download -v run
```

### 環境変数ファイルの使用

`.env` ファイルを使用する場合：

```bash
docker run --rm \
  --env-file .env \
  -v ./data:/app/data \
  mizucopo/yt-live-download run
```

## ロック機能

二重起動防止のためのファイルロック機能を備えています。

- **ロックファイル**: `{DOWNLOAD_DIR}/.app.lock`
- **動作**:
  - ロックファイルが存在し、`LOCK_STALE_HOURS`時間以内 → プログラム終了（他のインスタンスが実行中）
  - ロックファイルが存在し、`LOCK_STALE_HOURS`時間経過 → RuntimeError（古いロックファイルの検出）
  - ロックファイルなし → ロックを取得して処理続行

```bash
# ロックファイルを手動で削除
python -m src.main unlock
```

## テスト

```bash
# リント・型チェック・テストを一括実行
uv run task test

# テストのみ実行
uv run pytest
```

## ライセンス

MIT License

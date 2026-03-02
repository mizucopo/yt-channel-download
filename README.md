# YouTube Live Archive Downloader

YouTubeチャンネルの動画を自動的に検出・ダウンロードし、サムネイルを抽出してGoogle Driveへアップロード、その後ローカルファイルを削除するシステム。

## 機能

- **自動検出**: 指定チャンネルのライブ配信アーカイブをYouTube APIで検出
- **ダウンロード**: yt-dlpを使用した高品質動画ダウンロード
- **サムネイル抽出**: ffmpegで指定間隔のスクリーンショットを抽出
- **Google Driveアップロード**: mizu-common-pyのGoogleDriveProviderを使用
- **自動クリーンアップ**: アップロード完了後のローカルファイル削除
- **中断回復**: 処理が中断されたストリームの自動回復
- **Discord通知**: アップロード完了時にDiscordへ通知（オプション）

## 状態遷移

```
discovered → downloading → downloaded → thumbs_done → uploading → uploaded → cleaned
canceled (初回検出時のスキップ状態)
```

## 必要条件

**ローカル実行の場合:**
- Python 3.14+
- yt-dlp（動画ダウンロード用）
- ffmpeg（サムネイル抽出用）
- Google OAuth認証情報

**Dockerの場合:**
- Docker
- Google OAuth認証情報

## インストール

```bash
# リポジトリをクローン
git clone https://github.com/mizucopo/yt-channel-download.git
cd yt-channel-download

# 依存関係をインストール
uv sync
```

## 設定

環境変数または`.env`ファイルで設定します。

```bash
# .env.example をコピーして設定
cp .env.example .env
# .env を編集して必要な値を設定
```

> **初回セットアップ時**: Google OAuth 認証情報の取得方法は [docs/google_oauth_setup.md](docs/google_oauth_setup.md) を参照してください。

| 環境変数 | 説明 | デフォルト |
|---------|------|-----------|
| `YOUTUBE_CHANNEL_IDS` | 対象チャンネルID（カンマ区切り） | （必須） |
| `GOOGLE_OAUTH_CLIENT_ID` | Google OAuth クライアントID | （必須） |
| `GOOGLE_OAUTH_CLIENT_SECRET` | Google OAuth クライアントシークレット | `` |
| `GOOGLE_REFRESH_TOKEN` | Google OAuth リフレッシュトークン | （必須） |
| `GDRIVE_ROOT_FOLDER_ID` | Google DriveルートフォルダID | （必須） |
| `DATABASE_PATH` | データベースファイルパス | `data/databases/streams.db` |
| `DOWNLOAD_DIR` | ダウンロードディレクトリ | `data/downloads` |
| `THUMBNAIL_DIR` | サムネイルディレクトリ | `data/thumbnails` |
| `THUMBNAIL_INTERVAL` | サムネイル抽出間隔（秒） | `60` |
| `THUMBNAIL_QUALITY` | サムネイル画質（1-31、小さいほど高画質） | `2` |
| `MAX_RETRIES` | 最大リトライ回数 | `3` |
| `LOCK_STALE_HOURS` | ロックファイルの有効期限（時間） | `3` |
| `DISCORD_WEBHOOK_URL` | Discord Webhook URL（通知機能を使用する場合） | （なし） |

> **チャンネルIDの取得方法**: [docs/channel_id_setup.md](docs/channel_id_setup.md) を参照してください。

## 使用方法

### CLIコマンド

```bash
# 全パイプラインを実行（中断されたストリームの自動復旧を含む）
# -f/--full または -d/--days のいずれかが必須
uv run python -m src.main run --full        # フルスキャン（全期間）
uv run python -m src.main run --days 7      # 過去7日分をスキャン

# ステータス確認
uv run python -m src.main status

# ロックファイル削除
uv run python -m src.main unlock

# 再ダウンロード対象に設定
uv run python -m src.main redownload VIDEO_ID

# Google OAuth認証
uv run python -m src.main auth
```

### オプション

```bash
# 詳細ログを有効にする（グローバルオプション）
uv run python -m src.main -v run --full
```

> **初回起動時**: `--days`オプションは使用できません。必ず`--full`を指定してください。

## Docker

Dockerイメージを使用して実行できます。

```bash
# イメージを取得
docker pull mizucopo/yt-channel-download

# ヘルプ表示
docker run --rm mizucopo/yt-channel-download --help

# 全パイプラインを実行（-f/--full または -d/--days が必須）
docker run --rm \
  -e YOUTUBE_CHANNEL_IDS="channel_id1,channel_id2" \
  -e GOOGLE_OAUTH_CLIENT_ID="your_client_id" \
  -e GOOGLE_OAUTH_CLIENT_SECRET="your_client_secret" \
  -e GOOGLE_REFRESH_TOKEN="your_refresh_token" \
  -e GDRIVE_ROOT_FOLDER_ID="your_folder_id" \
  -v ./data:/app/data \
  mizucopo/yt-channel-download run --full

# 過去7日分をスキャン（2回目以降）
docker run --rm \
  -e YOUTUBE_CHANNEL_IDS="..." \
  -e GOOGLE_OAUTH_CLIENT_ID="..." \
  -e GOOGLE_OAUTH_CLIENT_SECRET="..." \
  -e GOOGLE_REFRESH_TOKEN="..." \
  -e GDRIVE_ROOT_FOLDER_ID="..." \
  -v ./data:/app/data \
  mizucopo/yt-channel-download run --days 7

# 詳細ログを有効にする（-v はグローバルオプション）
docker run --rm \
  -e YOUTUBE_CHANNEL_IDS="..." \
  -e GOOGLE_OAUTH_CLIENT_ID="..." \
  -e GOOGLE_OAUTH_CLIENT_SECRET="..." \
  -e GOOGLE_REFRESH_TOKEN="..." \
  -e GDRIVE_ROOT_FOLDER_ID="..." \
  -v ./data:/app/data \
  mizucopo/yt-channel-download -v run --full
```

### 環境変数ファイルの使用

`.env` ファイルを使用する場合：

```bash
docker run --rm \
  --env-file .env \
  -v ./data:/app/data \
  mizucopo/yt-channel-download run --full
```

## 詳細ドキュメント

- [チャンネルIDの取得](docs/channel_id_setup.md) - YouTubeチャンネルIDの調べ方
- [ロック機能](docs/lock.md) - 二重起動防止の仕様
- [GitHub Actions](docs/github_actions.md) - CI/CDワークフローの詳細
- [Google OAuth セットアップ](docs/google_oauth_setup.md) - 認証情報の取得方法

## テスト

```bash
# リント・型チェック・テストを一括実行
uv run task test

# テストのみ実行
uv run pytest
```

## ライセンス

[MIT License](LICENSE)

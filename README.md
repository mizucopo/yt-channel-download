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
```

## 必要条件

- Python 3.14+
- ffmpeg（サムネイル抽出用）
- Google Drive API認証情報

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

| 環境変数 | 説明 | デフォルト |
|---------|------|-----------|
| `YOUTUBE_API_KEY` | YouTube Data API v3キー | （必須） |
| `YOUTUBE_CHANNEL_IDS` | 対象チャンネルID（カンマ区切り） | （必須） |
| `DATABASE_PATH` | データベースファイルパス | `data/streams.db` |
| `DOWNLOAD_DIR` | ダウンロードディレクトリ | `data/downloads` |
| `THUMBNAIL_DIR` | サムネイルディレクトリ | `data/thumbnails` |
| `GDRIVE_CREDENTIALS_PATH` | Google Drive認証情報パス | `credentials.json` |
| `GDRIVE_ROOT_FOLDER_ID` | Google DriveルートフォルダID | （必須） |
| `THUMBNAIL_INTERVAL` | サムネイル抽出間隔（秒） | `60` |
| `MAX_RETRIES` | 最大リトライ回数 | `3` |

## 使用方法

### CLIコマンド

```bash
# 全パイプラインを実行
python -m src.main run

# 個別ステージの実行
python -m src.main discover   # 動画検出のみ
python -m src.main download   # ダウンロードのみ
python -m src.main thumbs     # サムネイル抽出のみ
python -m src.main upload     # アップロードのみ
python -m src.main cleanup    # クリーンアップのみ
python -m src.main recover    # 中断回復

# ステータス確認
python -m src.main status

# 個別動画の操作
python -m src.main download-one VIDEO_ID
python -m src.main upload-one VIDEO_ID
```

### オプション

```bash
# 詳細ログを有効にする
python -m src.main -v run
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

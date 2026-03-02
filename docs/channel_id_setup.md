# YouTube チャンネルIDの取得方法

`YOUTUBE_CHANNEL_IDS` 環境変数に設定するチャンネルID（`UC...`で始まる文字列）の取得方法を説明します。

## チャンネルIDとは

YouTubeチャンネルには以下の2つの識別子があります：

- **チャンネルID**: `UCxxxxxxxxxxxxxxxxxx` 形式（24文字）
- **ハンドル**: `@username` 形式

このプロジェクトでは**チャンネルID**を使用します。

## 取得方法

### 方法1: yt-dlp を使用（推奨）

yt-dlp がインストールされている場合、以下のコマンドで取得できます：

```bash
yt-dlp --print channel_id "https://www.youtube.com/@channel-handle"
```

例：
```bash
yt-dlp --print channel_id "https://www.youtube.com/@mizu-life-channel"
# 出力例: UCxxxxxxxxxxxxxxxxxx
```

### 方法2: ブラウザで確認

1. 対象のYouTubeチャンネルページを開く
2. ページのソースを表示（右クリック → 「ページのソースを表示」）
3. `channelId` で検索
4. `"UC..."` 形式の文字列を見つける

例：
```html
"channelId":"UCxxxxxxxxxxxxxxxxxx"
```

### 方法3: YouTube Studio で確認

1. YouTube Studio にログイン
2. 左メニューの「設定」→「チャンネル」→「基本情報」
3. チャンネルIDが表示されます（自分のチャンネルの場合）

## 設定

取得したチャンネルIDを `.env` ファイルに設定します：

```bash
# 単一チャンネル
YOUTUBE_CHANNEL_IDS=UCxxxxxxxxxxxxxxxxxx

# 複数チャンネル（カンマ区切り）
YOUTUBE_CHANNEL_IDS=UCxxxxxxxxxxxxxxxxxx,UCyyyyyyyyyyyyyyyyyy
```

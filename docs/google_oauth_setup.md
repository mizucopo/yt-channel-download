# Google OAuth 認証情報の取得手順

`GOOGLE_OAUTH_CLIENT_ID` と `GOOGLE_OAUTH_CLIENT_SECRET` の取得手順

## 1. Google Cloud プロジェクト作成

1. [Google Cloud Console](https://console.cloud.google.com/) にアクセス
2. 「新しいプロジェクト」を作成（既存プロジェクトでも可）

## 2. API 有効化

1. 「API とサービス」 > 「ライブラリ」を選択
2. 以下の API を有効化
   - Google Drive API
   - YouTube Data API v3

## 3. Google 認証プラットフォームの設定

1. 「OAuth 同意画面」に移動
2. 「ブランディング」を設定
3. 「データアクセス」にて以下のスコープを追加
   - `https://www.googleapis.com/auth/drive.file`
   - `https://www.googleapis.com/auth/youtube.readonly`
4. 「対象」にてテストユーザーに自分の Google アカウントを追加
   - 「本番環境」の場合は「テストに戻る」でテスト中に変更

## 4. OAuth クライアント ID 作成

1. 「OAuth 同意画面」に移動
2. 「クライアント」 > 「クライアントを作成」を選択
3. アプリケーションの種類： テレビと入力制限のあるデバイス」を選択
   > [!IMPORTANT]
   > このツールは Device Flow を使用するため、このタイプを選択
4. クライアント ID と クライアント シークレット を控え `.env` に設定

## 5. リフレッシュトークン取得

1. 以下を実行
   ```bash
   uv run python -m src.main auth
   ```
2. 表示される URL でコードを入力しログイン
3. 取得した `GOOGLE_REFRESH_TOKEN` を `.env` に設定

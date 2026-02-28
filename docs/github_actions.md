# GitHub Actions

以下のワークフローが設定されています。

## PR Quality Checks

プルリクエスト作成時に自動実行される品質チェック。

- **トリガー**: プルリクエスト作成・更新時
- **チェック内容**:
  - pytest（テスト）
  - mypy（型チェック）
  - ruff format（フォーマットチェック）
  - ruff check（リント）

## PR Tag Conflict Check

mainブランチへのPR時にバージョンタグの重複をチェック。

- **トリガー**: mainブランチへのプルリクエスト時
- **内容**: `pyproject.toml`のバージョンが既存のgitタグと重複していないか確認

## Docker Release

mainブランチへのマージ時にDockerイメージをビルド・プッシュし、GitHub Releaseを作成。

- **トリガー**: mainブランチへのpush、または手動実行
- **内容**:
  - Dockerイメージのビルド
  - Docker Hubへのプッシュ（`latest`タグとバージョンタグ）
  - gitタグの作成
  - GitHub Releaseの作成

### 必要なSecrets

| Secret名 | 説明 |
|---------|------|
| `DOCKERHUB_TOKEN` | Docker Hubのアクセストークン |

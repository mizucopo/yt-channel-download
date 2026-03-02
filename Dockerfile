FROM python:3.14-alpine AS builder

# git をインストール（mizu-common-py の取得に必要）
RUN apk add --no-cache git

# uv をインストール
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

# プロジェクト全体をコピー
COPY pyproject.toml uv.lock* ./
COPY src/ ./src/
COPY stubs/ ./stubs/

# 依存関係とプロジェクトをインストール
RUN uv sync --frozen --no-dev


FROM python:3.14-alpine

# ffmpeg をインストール
RUN apk add --no-cache ffmpeg

WORKDIR /app

# 仮想環境とソースコードをコピー
COPY --from=builder /app/.venv /app/.venv
COPY --from=builder /app/src /app/src
COPY --from=builder /app/stubs /app/stubs

# データディレクトリを作成
RUN mkdir -p /app/data/databases /app/data/downloads /app/data/thumbnails

# 環境変数を設定
ENV PATH="/app/.venv/bin:$PATH"
ENV DATABASE_PATH=/app/data/databases/streams.db
ENV DOWNLOAD_DIR=/app/data/downloads
ENV THUMBNAIL_DIR=/app/data/thumbnails

ENTRYPOINT ["python", "-m", "src.main"]
CMD ["--help"]

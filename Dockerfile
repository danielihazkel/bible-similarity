# syntax=docker/dockerfile:1
# The public read-only server (docs/DEPLOY.md): the viewer and the API over a bundle written by
# `bsim deploy-bundle`, mounted read-only at /app/bundle. Nothing personal, no query encoder, so
# no ML libraries in the image (`uv sync --no-default-groups`: pyproject's `ml` group left out).
#
#   uv run bsim deploy-bundle [--no-nc]
#   docker build -t bsim-public .
#   docker run --rm -p 8000:8000 -v "$PWD/bundle:/app/bundle:ro" bsim-public

# 1. the viewer (web/dist)
FROM node:24.14.0-slim AS web
WORKDIR /app/web
COPY web/package.json web/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY web/ ./
RUN npm run build

# 2. the server
FROM python:3.11.14-slim AS app
COPY --from=ghcr.io/astral-sh/uv:0.9.20 /uv /usr/local/bin/uv
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy UV_PYTHON_DOWNLOADS=never
WORKDIR /app
COPY pyproject.toml uv.lock README.md ./
RUN uv sync --frozen --no-default-groups --no-install-project
COPY src/ src/
COPY configs/ configs/
RUN uv sync --frozen --no-default-groups
COPY --from=web /app/web/dist web/dist
RUN useradd --system --uid 10001 bsim && mkdir -p bundle cache && chown bsim cache
USER bsim
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=60s \
  CMD ["/app/.venv/bin/python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/books', timeout=4)"]
CMD ["/app/.venv/bin/bsim", "serve", "--config", "configs/docker.yaml"]

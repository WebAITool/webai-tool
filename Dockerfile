FROM python:3.12-slim
COPY --from=ghcr.io/astral-sh/uv:0.11.18 /uv /uvx /bin/

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app/src
ENV PLAYWRIGHT_BROWSERS_PATH=/ms-playwright

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
    git \
    nodejs \
    npm \
    tree \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml uv.lock README.md ./

RUN uv sync --frozen --no-dev --no-install-project \
    && .venv/bin/python -m playwright install --with-deps chromium

RUN useradd --create-home --uid 10001 appuser \
    && mkdir -p /workspace /ms-playwright \
    && chown -R appuser:appuser /app /workspace /ms-playwright

COPY --chown=appuser:appuser src ./src

USER appuser
WORKDIR /workspace

ENTRYPOINT ["/app/.venv/bin/python", "/app/src/main.py"]
CMD ["--help"]

# Contexte de build : la racine du dépôt (voir docker-compose.yml), l'API dépend de packages/engine et packages/generator.
FROM python:3.12-slim
COPY --from=ghcr.io/astral-sh/uv:0.12.23 /uv /bin/uv
WORKDIR /srv
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy UV_PYTHON_DOWNLOADS=never PATH="/srv/.venv/bin:$PATH"
COPY pyproject.toml uv.lock .python-version ./
RUN uv sync --frozen --no-dev --no-install-project
COPY packages/engine packages/engine
COPY packages/generator packages/generator
COPY apps/api/app apps/api/app
RUN uv sync --frozen --no-dev --no-editable
RUN useradd --system app
USER app
EXPOSE 8000
HEALTHCHECK --interval=5s --timeout=3s --retries=30 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/health')"
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers"]

FROM python:3.13-slim AS builder

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/
WORKDIR /app
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

# Instalacja narzędzi budowania oraz kompilacja biblioteki lgpio ze źródeł
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    swig \
    python3-dev \
    git \
    make \
    && git clone https://github.com/joan2937/lg.git /tmp/lg \
    && cd /tmp/lg \
    && make \
    && make install \
    && rm -rf /tmp/lg \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-install-project --no-dev

COPY . .
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev


FROM python:3.13-slim

WORKDIR /app

COPY --from=builder /usr/local/lib/liblgpio* /usr/local/lib/
RUN ldconfig

COPY --from=builder /app /app
COPY --from=builder /app/.venv /app/.venv

ENV PATH="/app/.venv/bin:$PATH"
CMD ["/app/.venv/bin/python", "movement_det.py"]

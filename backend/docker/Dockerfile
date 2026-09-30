ARG PYTHON_TAG=3.13.8-alpine3.22@sha256:3a77fbbb5bc88c0f63cc2692a13b011547f25ee93536e991544c452801856226
ARG UV_VERSION=0.12.7

FROM python:${PYTHON_TAG} AS builder

ARG UV_VERSION

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never

WORKDIR /opt/app

RUN python3 -m pip install --no-cache-dir "uv==${UV_VERSION}"

COPY pyproject.toml uv.lock ./
RUN uv sync --locked --no-dev --no-install-project

COPY src ./src
COPY alembic.ini ./
COPY migrations ./migrations

RUN uv sync --locked --no-dev --no-editable

FROM python:${PYTHON_TAG}

ENV PATH="/opt/app/.venv/bin:${PATH}" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN addgroup -S app \
    && adduser -S -G app -h /home/app app

WORKDIR /opt/app

COPY --from=builder --chown=app:app /opt/app/.venv ./.venv
COPY --from=builder --chown=app:app /opt/app/alembic.ini ./alembic.ini
COPY --from=builder --chown=app:app /opt/app/migrations ./migrations

USER app

EXPOSE 8000

##### image tags #####
ARG PYTHON_TAG=3.13.8-alpine3.22@sha256:cbec402ae64582d007ae7e2050f2c977a51491c4ef466f52569786686a79142a
ARG UV_VERSION=0.12.7

##### build #####
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

RUN uv sync --locked --no-dev --no-editable

##### runtime #####
FROM python:${PYTHON_TAG}

ENV PATH="/opt/app/.venv/bin:${PATH}" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN addgroup -S app \
    && adduser -S -G app -h /home/app app

WORKDIR /opt/app

COPY --from=builder --chown=app:app /opt/app/.venv ./.venv

USER app

EXPOSE 8000

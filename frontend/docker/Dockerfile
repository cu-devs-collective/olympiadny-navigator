##### image tags #####
ARG NODE_TAG=24-alpine3.24@sha256:ebfe2f90462722a7a4de65e91990e97fe0d401c70e0e762c5b53302f905ec1c1
ARG NGINX_TAG=1.29.8-alpine3.23@sha256:5616878291a2eed594aee8db4dade5878cf7edcb475e59193904b198d9b830de
ARG PNPM_VERSION=12.4.2

##### build #####
FROM node:${NODE_TAG} AS dependencies

ARG PNPM_VERSION

ENV PNPM_HOME=/pnpm
ENV PATH=${PNPM_HOME}:${PATH}

RUN corepack enable \
    && corepack install --global "pnpm@${PNPM_VERSION}"

WORKDIR /opt/app

COPY frontend/package.json frontend/pnpm-lock.yaml ./frontend/

WORKDIR /opt/app/frontend

RUN pnpm install --frozen-lockfile

FROM dependencies AS source

WORKDIR /opt/app

COPY backend/spec/openapi.yaml ./backend/spec/openapi.yaml
COPY frontend/index.html frontend/openapi-ts.config.ts frontend/tsconfig*.json frontend/vite.config.ts ./frontend/
COPY frontend/public ./frontend/public
COPY frontend/src ./frontend/src

FROM source AS development

WORKDIR /opt/app/frontend

EXPOSE 5173

CMD ["pnpm", "dev", "--", "--host", "0.0.0.0", "--port", "5173"]

FROM source AS builder

WORKDIR /opt/app/frontend

RUN pnpm build

FROM nginx:${NGINX_TAG} AS runtime

COPY frontend/docker/nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=builder /opt/app/frontend/dist /usr/share/nginx/html

EXPOSE 80

HEALTHCHECK --interval=10s --timeout=3s --start-period=5s --retries=3 \
    CMD wget --quiet --output-document=/dev/null http://127.0.0.1/healthz || exit 1

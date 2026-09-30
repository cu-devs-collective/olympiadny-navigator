# Интерфейс Олимпиадного навигатора

React, TypeScript и Vite. Инструкции по запуску всего проекта находятся в [корневом README](../README.md).

## Разработка

Нужны Node.js 24+ и pnpm.

```bash
pnpm install --frozen-lockfile
pnpm dev
```

Интерфейс доступен на http://localhost:5173. Запросы `/api` проксируются на `http://localhost:8000`. Другой адрес backend можно задать через `VITE_API_PROXY_TARGET`.

## API

Файлы в `src/api/` генерируются из `backend/spec/openapi.yaml` с помощью `@hey-api/openapi-ts`. Обновление: `pnpm generate:api`. Генерация также запускается перед `pnpm dev` и `pnpm build`.

## Проверки

```bash
pnpm lint
pnpm typecheck
pnpm build
pnpm exec playwright install chromium
pnpm test:e2e
```

Для тестов с установленным Chrome: `PLAYWRIGHT_CHANNEL=chrome pnpm test:e2e`.

## Docker

Образ собирается из корня репозитория:

```bash
docker build -f frontend/docker/Dockerfile -t max-bot-frontend .
```

Nginx слушает порт 80 и направляет запросы `/api` в сервис `api:8000`. Проверка готовности контейнера: `/healthz`.

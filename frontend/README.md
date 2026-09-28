# Frontend

## API client

The typed API client in `src/api` is generated from
`../backend/spec/openapi.yaml` with `@hey-api/openapi-ts`. Generated Zod
schemas validate request and response data at runtime.

```sh
pnpm generate:api
```

API generation also runs automatically before `pnpm dev` and `pnpm build`.
During local development, Vite proxies `/api` requests to
`http://localhost:8000`.

Do not edit files under `src/api` manually. Update the backend API schema and
regenerate the client instead.

## Docker

Build the production image from the repository root so the OpenAPI schema is
available during client generation:

```sh
docker build -f frontend/docker/Dockerfile -t max-bot-frontend .
```

The container serves the frontend on port `80`, exposes `/healthz`, and proxies
`/api` to the `api:8000` service on its Docker network. The API hostname is
resolved per request, so the frontend starts normally when the API container is
unavailable; API requests return `502` until it becomes reachable.

For development with Vite and HMR:

```sh
make up
make logs
```

The development frontend is available at `http://localhost:5173`. By default,
its `/api` proxy targets the backend at `http://host.docker.internal:8000`.
Override `FRONTEND_PORT` or `VITE_API_PROXY_TARGET` when needed.

Run `make help` to see the local and Docker development commands.

# React + TypeScript + Vite

This template provides a minimal setup to get React working in Vite with HMR and some ESLint rules.

Currently, two official plugins are available:

- [@vitejs/plugin-react](https://github.com/vitejs/vite-plugin-react/blob/main/packages/plugin-react) uses [Oxc](https://oxc.rs)
- [@vitejs/plugin-react-swc](https://github.com/vitejs/vite-plugin-react/blob/main/packages/plugin-react-swc) uses [SWC](https://swc.rs/)

## React Compiler

The React Compiler is not enabled on this template because of its impact on dev & build performances. To add it, see [this documentation](https://react.dev/learn/react-compiler/installation).

## Expanding the ESLint configuration

If you are developing a production application, we recommend updating the configuration to enable type-aware lint rules:

```js
export default defineConfig([
  globalIgnores(['dist']),
  {
    files: ['**/*.{ts,tsx}'],
    extends: [
      // Other configs...

      // Remove tseslint.configs.recommended and replace with this
      tseslint.configs.recommendedTypeChecked,
      // Alternatively, use this for stricter rules
      tseslint.configs.strictTypeChecked,
      // Optionally, add this for stylistic rules
      tseslint.configs.stylisticTypeChecked,

      // Other configs...
    ],
    languageOptions: {
      parserOptions: {
        project: ['./tsconfig.node.json', './tsconfig.app.json'],
        tsconfigRootDir: import.meta.dirname,
      },
      // other options...
    },
  },
])

```

You can also install [eslint-plugin-react-x](https://npmx.dev/package/eslint-plugin-react-x) and [eslint-plugin-react-dom](https://npmx.dev/package/eslint-plugin-react-dom) for React-specific lint rules:

```js
// eslint.config.js
import reactX from 'eslint-plugin-react-x'
import reactDom from 'eslint-plugin-react-dom'

export default defineConfig([
  globalIgnores(['dist']),
  {
    files: ['**/*.{ts,tsx}'],
    extends: [
      // Other configs...
      // Enable lint rules for React
      reactX.configs['recommended-typescript'],
      // Enable lint rules for React DOM
      reactDom.configs.recommended,
    ],
    languageOptions: {
      parserOptions: {
        project: ['./tsconfig.node.json', './tsconfig.app.json'],
        tsconfigRootDir: import.meta.dirname,
      },
      // other options...
    },
  },
])

```

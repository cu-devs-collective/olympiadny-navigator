import { defineConfig } from "@hey-api/openapi-ts";

export default defineConfig({
  input: "../backend/spec/openapi.yaml",
  output: "src/api",
  plugins: [
    {
      name: "@hey-api/client-fetch",
      throwOnError: true,
    },
    "@hey-api/typescript",
    "zod",
    {
      name: "@hey-api/sdk",
      responseStyle: "data",
      validator: "zod",
    },
  ],
});

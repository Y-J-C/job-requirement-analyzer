# API Contract

`openapi.json` is generated from the FastAPI application and is the source for the web client's
TypeScript definitions. Do not edit it or `apps/web/src/generated/api-schema.ts` manually.

Regenerate both artifacts from the repository root:

```powershell
pnpm api:contract:generate
```

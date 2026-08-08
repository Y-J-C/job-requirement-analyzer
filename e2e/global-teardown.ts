import { request } from "@playwright/test";

import { apiBaseUrl, cleanupRunResources } from "./support/api";

export default async function globalTeardown(): Promise<void> {
  const api = await request.newContext({ baseURL: apiBaseUrl });
  try {
    await cleanupRunResources(api);
  } finally {
    await api.dispose();
  }
}

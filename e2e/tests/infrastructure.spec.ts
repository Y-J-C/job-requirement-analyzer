import { expect, test } from "@playwright/test";

import {
  createTargetRole,
  deleteTargetRole,
  getTargetRole,
  apiBaseUrl,
  taggedName,
} from "../support/api";

test("基础服务可以通过浏览器测试访问", async ({ page, request }) => {
  const healthResponse = await request.get(`${apiBaseUrl}/health`);
  expect(healthResponse.ok()).toBe(true);
  await expect(healthResponse.json()).resolves.toEqual({ status: "ok" });

  await page.goto("/");
  await expect(page).toHaveTitle(/岗位门槛分析系统/);
  await expect(page.getByRole("button", { name: "退出登录" })).toHaveCount(0);
  await expect(page.getByRole("heading", { name: "岗位门槛分析系统" })).toBeVisible();
});

test("测试目标方向可以通过公开 API 完整清理", async ({ request }) => {
  const role = await createTargetRole(request, taggedName("基础设施清理"));

  try {
    const response = await getTargetRole(request, role.id);
    expect(response.ok()).toBe(true);
  } finally {
    await deleteTargetRole(request, role.id);
  }

  const deletedResponse = await getTargetRole(request, role.id);
  expect(deletedResponse.status()).toBe(404);
});

test("全局清理会删除本次运行遗留的目标方向", async ({ request }) => {
  const role = await createTargetRole(request, taggedName("全局清理"));

  const response = await getTargetRole(request, role.id);
  expect(response.ok()).toBe(true);
});

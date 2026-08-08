import { expect, test } from "@playwright/test";

import { apiBaseUrl, createTargetRole, taggedName } from "../support/api";

test("错误处理会在岗位保存请求失败时显示可恢复提示", async ({ page, request }) => {
  const role = await createTargetRole(request, taggedName("网络错误处理"));
  const jobsLoaded = page.waitForResponse((response) => (
    response.request().method() === "GET"
    && response.url().endsWith(`/api/v1/target-roles/${role.id}/jobs`)
  ));
  await page.goto(`/target-roles/${role.id}`);
  await jobsLoaded;

  await page.getByLabel("公司名称").fill(taggedName("网络错误示例科技"));
  await page.getByLabel("岗位名称").fill("测试岗位");
  await page.getByLabel("JD 原文").fill("熟练使用 SQL");
  await page.route(
    `${apiBaseUrl}/api/v1/target-roles/${role.id}/jobs`,
    (route) => route.abort("connectionfailed"),
  );
  await page.getByRole("button", { name: "保存岗位" }).click();

  await expect(page.getByRole("alert").filter({
    hasText: "岗位保存失败，请检查输入和 API 状态后重试。",
  })).toBeVisible();
  const jobs = await request.get(
    `${apiBaseUrl}/api/v1/target-roles/${role.id}/jobs`,
  );
  expect((await jobs.json()).total).toBe(0);
});

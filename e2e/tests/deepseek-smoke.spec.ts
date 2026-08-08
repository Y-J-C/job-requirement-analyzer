import { expect, test } from "@playwright/test";

import { createTargetRole, taggedName } from "../support/api";

test("@deepseek 真实模型可以完成提取、确认和汇总", async ({ page, request }) => {
  test.skip(
    process.env.RUN_DEEPSEEK_E2E !== "1",
    "仅在显式设置 RUN_DEEPSEEK_E2E=1 时调用真实模型",
  );
  test.setTimeout(120_000);

  const role = await createTargetRole(request, taggedName("DeepSeek 冒烟"));
  const companyName = taggedName("模型示例科技");
  const jobTitle = "数据分析实习生";
  const jobsLoaded = page.waitForResponse((response) => (
    response.request().method() === "GET"
    && response.url().endsWith(`/api/v1/target-roles/${role.id}/jobs`)
  ));
  await page.goto(`/target-roles/${role.id}`);
  await jobsLoaded;

  await page.getByLabel("公司名称").fill(companyName);
  await page.getByLabel("岗位名称").fill(jobTitle);
  await page.getByLabel("JD 原文").fill("岗位要求：熟练使用 SQL。");
  await page.getByRole("button", { name: "保存岗位" }).click();
  await page.getByRole("link", { name: "审核门槛 →" }).click();

  await page.getByRole("button", { name: "使用 DeepSeek 提取门槛" }).click();
  await expect(page.getByRole("status").filter({
    hasText: "提取完成。请逐条核对后确认整份岗位。",
  })).toBeVisible({ timeout: 100_000 });
  await expect(page.getByRole("listitem").first()).toBeVisible();

  page.once("dialog", (dialog) => dialog.accept());
  await page.getByRole("button", { name: "确认整份岗位" }).click();
  await expect(page.getByText("已确认", { exact: true }).first()).toBeVisible();

  await page.getByRole("link", { name: "← 返回岗位方向" }).click();
  await page.getByRole("link", { name: "查看确认汇总 →" }).click();
  await expect(page.getByRole("heading", { name: `${role.name} · 确认汇总` })).toBeVisible();
  await expect(page.getByText("100%", { exact: true })).toBeVisible();
});

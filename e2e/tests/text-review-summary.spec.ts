import { expect, test } from "@playwright/test";

import { taggedName } from "../support/api";

test("文本主流程可以审核确认并回溯汇总证据", async ({ page }) => {
  const roleName = taggedName("文本主流程");
  const companyName = taggedName("示例科技");
  const jobTitle = "数据分析实习生";
  const originalText = "熟练使用 SQL，并能够独立完成数据分析报告。";

  const initialRolesLoaded = page.waitForResponse((response) => (
    response.request().method() === "GET"
    && response.url().endsWith("/api/v1/target-roles")
  ));
  await page.goto("/");
  await initialRolesLoaded;
  await page.getByLabel("方向名称").fill(roleName);
  await page.getByLabel("说明（可选）").fill("验证文本、审核、确认与汇总闭环");
  await page.getByRole("button", { name: "创建目标方向" }).click();
  await page.getByRole("link", { name: roleName, exact: true }).click();

  await page.getByLabel("公司名称（可选提示）").fill(companyName);
  await page.getByLabel("岗位名称（可选提示）").fill(jobTitle);
  await page.getByLabel("岗位原文").fill(originalText);
  await page.getByRole("button", { name: "提交并自动分析" }).click();
  await expect(page.getByRole("heading", { name: `${companyName} · ${jobTitle}` })).toBeVisible();
  await page.getByRole("link", { name: "审核指标与元数据 →" }).click({ timeout: 15_000 });

  await expect(page.getByRole("heading", { name: `${companyName} · ${jobTitle}` })).toBeVisible();
  await expect(page.getByText(originalText, { exact: true })).toBeVisible();
  await expect(page.getByRole("heading", { name: "SQL", exact: true })).toBeVisible();

  await page.getByRole("button", { name: "编辑 SQL" }).click();
  await page.getByLabel("编辑标准条件名称").fill("SQL 查询");
  await page.getByRole("button", { name: "保存修改" }).click();
  await expect(page.getByRole("heading", { name: "SQL 查询", exact: true })).toBeVisible();

  page.once("dialog", (dialog) => dialog.accept());
  await page.getByRole("button", { name: "确认整份岗位" }).click();
  await expect(page.getByText("已确认", { exact: true }).first()).toBeVisible();

  await page.getByRole("link", { name: "← 返回岗位方向" }).click();
  await page.getByRole("link", { name: "查看全部已确认岗位汇总 →" }).click();
  await expect(page.getByRole("heading", { name: `${roleName} · 确认汇总` })).toBeVisible();
  await expect(page.getByRole("heading", { name: "SQL 查询", exact: true })).toBeVisible();
  await expect(page.getByText("100%", { exact: true })).toBeVisible();
  await page.getByText("查看 1 条原文证据", { exact: true }).click();
  await expect(page.getByText("熟练使用 SQL", { exact: true })).toBeVisible();
});

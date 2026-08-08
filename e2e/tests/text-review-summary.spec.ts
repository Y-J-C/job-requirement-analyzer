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

  await page.getByLabel("公司名称").fill(companyName);
  await page.getByLabel("岗位名称").fill(jobTitle);
  await page.getByLabel("JD 原文").fill(originalText);
  await page.getByRole("button", { name: "保存岗位" }).click();
  await expect(page.getByRole("heading", { name: `${companyName} · ${jobTitle}` })).toBeVisible();
  await page.getByRole("link", { name: "审核门槛 →" }).click();

  await expect(page.getByRole("heading", { name: `${companyName} · ${jobTitle}` })).toBeVisible();
  await expect(page.getByText(originalText, { exact: true })).toBeVisible();
  await page.getByLabel("标准条件名称").fill("SQL");
  await page.getByLabel("原文依据").fill("熟练使用 SQL");
  await page.getByRole("button", { name: "新增门槛" }).click();
  await expect(page.getByRole("heading", { name: "SQL", exact: true })).toBeVisible();

  await page.getByRole("button", { name: "编辑 SQL" }).click();
  await page.getByLabel("编辑标准条件名称").fill("SQL 查询");
  await page.getByRole("button", { name: "保存修改" }).click();
  await expect(page.getByRole("heading", { name: "SQL 查询", exact: true })).toBeVisible();

  page.once("dialog", (dialog) => dialog.accept());
  await page.getByRole("button", { name: "确认整份岗位" }).click();
  await expect(page.getByText("已确认", { exact: true }).first()).toBeVisible();

  await page.getByRole("link", { name: "← 返回岗位方向" }).click();
  await page.getByRole("link", { name: "查看确认汇总 →" }).click();
  await expect(page.getByRole("heading", { name: `${roleName} · 确认汇总` })).toBeVisible();
  await expect(page.getByRole("heading", { name: "SQL 查询", exact: true })).toBeVisible();
  await expect(page.getByText("100%", { exact: true })).toBeVisible();
  await page.getByText("查看 1 条原文证据", { exact: true }).click();
  await expect(page.getByText("熟练使用 SQL", { exact: true })).toBeVisible();
});

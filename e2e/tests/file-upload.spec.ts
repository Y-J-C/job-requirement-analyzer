import path from "node:path";

import { expect, test } from "@playwright/test";

import { apiBaseUrl, createTargetRole, taggedName } from "../support/api";

test("文件主流程可以异步解析并在删除后清理源文件", async ({ page, request }) => {
  const role = await createTargetRole(request, taggedName("文件主流程"));
  const companyName = taggedName("文件示例科技");
  const jobTitle = "数据分析实习生";
  const fixture = path.join(process.cwd(), "e2e", "fixtures", "job-posting.md");

  const jobsLoaded = page.waitForResponse((response) => (
    response.request().method() === "GET"
    && response.url().endsWith(`/api/v1/target-roles/${role.id}/jobs`)
  ));
  await page.goto(`/target-roles/${role.id}`);
  await jobsLoaded;

  await page.getByRole("radio", { name: "上传文件" }).check();
  await page.getByLabel("公司名称").fill(companyName);
  await page.getByLabel("岗位名称").fill(jobTitle);
  await page.getByLabel("岗位文件").setInputFiles(fixture);
  const uploadCompleted = page.waitForResponse((response) => (
    response.request().method() === "POST"
    && response.url().endsWith(`/api/v1/target-roles/${role.id}/jobs/upload`)
  ));
  await page.getByRole("button", { name: "上传并提取" }).click();
  const uploadResponse = await uploadCompleted;
  expect(uploadResponse.status()).toBe(201);
  const uploaded = await uploadResponse.json() as {
    job: { id: string; status: string };
    source_file: { parse_status: string };
  };
  expect(uploaded.job.status).toBe("extracting");
  expect(uploaded.source_file.parse_status).toBe("pending");

  await expect(page.getByText("文件已保存，正在提取文本…", { exact: true })).toBeVisible();
  await expect(page.getByRole("link", { name: "审核门槛 →" })).toBeVisible({ timeout: 15_000 });
  await page.getByText("查看 JD 原文", { exact: true }).click();
  await expect(page.getByText("岗位要求：熟练使用 SQL，能够完成数据分析报告。"))
    .toBeVisible();

  await page.getByRole("link", { name: "审核门槛 →" }).click();
  await page.getByLabel("标准条件名称").fill("SQL");
  await page.getByLabel("原文依据").fill("熟练使用 SQL");
  await page.getByRole("button", { name: "新增门槛" }).click();
  page.once("dialog", (dialog) => dialog.accept());
  await page.getByRole("button", { name: "确认整份岗位" }).click();
  await expect(page.getByText("已确认", { exact: true }).first()).toBeVisible();

  await page.getByRole("link", { name: "← 返回岗位方向" }).click();
  page.once("dialog", (dialog) => dialog.accept());
  await page.getByRole("button", { name: "删除岗位" }).click();
  await expect(page.getByRole("heading", { name: `${companyName} · ${jobTitle}` })).toHaveCount(0);

  const deletedSource = await request.get(
    `${apiBaseUrl}/api/v1/jobs/${uploaded.job.id}/source-file`,
  );
  expect(deletedSource.status()).toBe(404);
});

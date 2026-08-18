import fs from "node:fs";
import path from "node:path";

import { expect, test } from "@playwright/test";

import { apiBaseUrl, createTargetRole, taggedName } from "../support/api";

const scannedPdfBase64 = "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";

test("文件主流程可以异步解析并在删除后清理源文件", async ({ page, request }) => {
  const role = await createTargetRole(request, taggedName("文件主流程"));
  const companyName = taggedName("文件示例科技");
  const jobTitle = "数据分析实习生";
  const fixture = path.join(process.cwd(), "e2e", "fixtures", "job-posting.md");

  const jobsLoaded = page.waitForResponse((response) => (
    response.request().method() === "GET"
    && response.url().includes(`/api/v1/target-roles/${role.id}/jobs?`)
  ));
  await page.goto(`/target-roles/${role.id}`);
  await jobsLoaded;

  await page.getByRole("radio", { name: "上传文档" }).check();
  await page.getByLabel("公司名称（可选提示）").fill(companyName);
  await page.getByLabel("岗位名称（可选提示）").fill(jobTitle);
  await page.getByLabel("岗位文档").setInputFiles(fixture);
  const uploadCompleted = page.waitForResponse((response) => (
    response.request().method() === "POST"
    && response.url().endsWith(`/api/v1/target-roles/${role.id}/jobs/intake`)
  ));
  await page.getByRole("button", { name: "提交并自动分析" }).click();
  const uploadResponse = await uploadCompleted;
  expect(uploadResponse.status()).toBe(201);
  const uploaded = await uploadResponse.json() as {
    job: { id: string; status: string };
    source_files: Array<{ parse_status: string }>;
  };
  expect(uploaded.job.status).toBe("extracting");
  expect(uploaded.source_files[0].parse_status).toBe("pending");

  await expect(page.getByText("来源已保存，正在提取文字…", { exact: true })).toBeVisible();
  await expect(page.getByRole("link", { name: "审核指标与元数据 →" })).toBeVisible({ timeout: 15_000 });
  await page.getByText("查看岗位原文", { exact: true }).click();
  await expect(page.getByText("岗位要求：熟练使用 SQL，能够完成数据分析报告。"))
    .toBeVisible();

  await page.getByRole("link", { name: "审核指标与元数据 →" }).click();
  await expect(page.getByRole("heading", { name: "SQL", exact: true })).toBeVisible();
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

test("扫描版 PDF 可以经 OCR 自动进入审核", async ({ page, request }, testInfo) => {
  const role = await createTargetRole(request, taggedName("扫描版 PDF"));
  const fixture = testInfo.outputPath("扫描岗位.pdf");
  fs.mkdirSync(path.dirname(fixture), { recursive: true });
  fs.writeFileSync(fixture, Buffer.from(scannedPdfBase64, "base64"));

  await page.goto(`/target-roles/${role.id}`);
  await page.getByRole("radio", { name: "上传文档" }).check();
  await page.getByLabel("岗位文档").setInputFiles(fixture);
  await page.getByRole("button", { name: "提交并自动分析" }).click();

  await expect(page.getByRole("link", { name: "审核指标与元数据 →" }))
    .toBeVisible({ timeout: 15_000 });
  await page.getByText("查看岗位原文", { exact: true }).click();
  await expect(page.getByText("E2E 图片岗位")).toBeVisible();
  await expect(page.getByText("熟练使用 SQL")).toBeVisible();
});

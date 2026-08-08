import { Buffer } from "node:buffer";

import { expect, test } from "@playwright/test";

import { apiBaseUrl, createTargetRole, taggedName } from "../support/api";

test("错误处理会拒绝不支持格式和超限文件且不创建岗位", async ({ page, request }) => {
  const role = await createTargetRole(request, taggedName("上传错误处理"));
  const jobsLoaded = page.waitForResponse((response) => (
    response.request().method() === "GET"
    && response.url().endsWith(`/api/v1/target-roles/${role.id}/jobs`)
  ));
  await page.goto(`/target-roles/${role.id}`);
  await jobsLoaded;

  await page.getByRole("radio", { name: "上传文件" }).check();
  await page.getByLabel("公司名称").fill(taggedName("错误示例科技"));
  await page.getByLabel("岗位名称").fill("测试岗位");
  await page.getByLabel("岗位文件").setInputFiles({
    name: "job.txt",
    mimeType: "text/plain",
    buffer: Buffer.from("不支持的文本扩展名", "utf8"),
  });
  const rejectedUpload = page.waitForResponse((response) => (
    response.request().method() === "POST"
    && response.url().endsWith(`/api/v1/target-roles/${role.id}/jobs/upload`)
  ));
  await page.getByRole("button", { name: "上传并提取" }).click();
  expect((await rejectedUpload).status()).toBe(422);
  await expect(page.getByRole("alert").filter({
    hasText: "文件格式不支持，请选择 PDF、Markdown 或 DOCX。",
  })).toBeVisible();

  await page.getByLabel("岗位文件").setInputFiles({
    name: "oversized.md",
    mimeType: "text/markdown",
    buffer: Buffer.alloc(10 * 1024 * 1024 + 1, 65),
  });
  await page.getByRole("button", { name: "上传并提取" }).click();
  await expect(page.getByRole("alert").filter({ hasText: "文件超过 10 MiB 限制。" }))
    .toBeVisible();

  const jobs = await request.get(
    `${apiBaseUrl}/api/v1/target-roles/${role.id}/jobs`,
  );
  expect(jobs.ok()).toBe(true);
  expect((await jobs.json()).total).toBe(0);
});

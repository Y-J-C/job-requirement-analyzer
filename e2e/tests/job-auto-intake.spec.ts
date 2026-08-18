import { Buffer } from "node:buffer";

import { expect, test } from "@playwright/test";

import { apiBaseUrl, createTargetRole, taggedName } from "../support/api";

const onePixelPng = Buffer.from(
  "iVBORw0KGgoAAAANSUhEUgAAAAIAAAACCAIAAAD91JpzAAAAE0lEQVR4nGP8//8/AwMDEwMYAAAkBgMBXaJOiAAAAABJRU5ErkJggg==",
  "base64",
);

test("多张岗位图片按选择顺序合并且只自动分析一次", async ({ page, request }) => {
  const role = await createTargetRole(request, taggedName("图片自动录入"));
  await page.goto(`/target-roles/${role.id}`);
  await page.getByRole("radio", { name: "上传图片" }).check();
  await page.getByLabel("公司名称（可选提示）").fill(taggedName("图片示例科技"));
  await page.getByLabel("岗位名称（可选提示）").fill("数据分析实习生");
  await page.getByLabel("岗位图片").setInputFiles([
    { name: "第一页.png", mimeType: "image/png", buffer: onePixelPng },
    { name: "第二页.png", mimeType: "image/png", buffer: onePixelPng },
  ]);
  await expect(page.getByRole("list", { name: "图片处理顺序" })).toContainText("第一页.png");
  await expect(page.getByRole("list", { name: "图片处理顺序" })).toContainText("第二页.png");

  const intakeResponse = page.waitForResponse((response) => (
    response.request().method() === "POST" && response.url().endsWith("/jobs/intake")
  ));
  await page.getByRole("button", { name: "提交并自动分析" }).click();
  const intake = await (await intakeResponse).json() as { job: { id: string } };
  await page.getByRole("link", { name: "审核指标与元数据 →" }).click({ timeout: 20_000 });
  await expect(page.getByText("E2E 图片岗位", { exact: false }).first()).toBeVisible();

  const runs = await request.get(
    `${apiBaseUrl}/api/v1/jobs/${intake.job.id}/analysis-runs/latest`,
  );
  expect(runs.ok()).toBe(true);
  expect((await runs.json()).version).toBe(1);
});

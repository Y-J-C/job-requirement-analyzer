import { expect, test } from "@playwright/test";

import { apiBaseUrl, createTargetRole, taggedName } from "../support/api";

test("只综合用户选中的第一个和第三个岗位", async ({ page, request }) => {
  const role = await createTargetRole(request, taggedName("选中岗位汇总"));
  const jobs: Array<{ id: string; company_name: string }> = [];
  for (const [company, requirement] of [["甲公司", "SQL"], ["乙公司", "Excel"], ["丙公司", "SQL"]]) {
    const created = await request.post(`${apiBaseUrl}/api/v1/target-roles/${role.id}/jobs`, {
      data: {
        company_name: company,
        job_title: "数据分析实习生",
        recruitment_stage: "daily_internship",
        original_text: `要求掌握 ${requirement}`,
      },
    });
    const job = await created.json() as { id: string; company_name: string };
    jobs.push(job);
    await request.post(`${apiBaseUrl}/api/v1/jobs/${job.id}/requirements`, {
      data: {
        normalized_name: requirement,
        requirement_type: "core_competency",
        original_text: `要求掌握 ${requirement}`,
        explicitness: "explicit",
      },
    });
    await request.post(`${apiBaseUrl}/api/v1/jobs/${job.id}/confirm-requirements`);
  }

  await page.goto(`/target-roles/${role.id}`);
  await page.getByLabel("选择 甲公司 · 数据分析实习生").check();
  await page.getByLabel("选择 丙公司 · 数据分析实习生").check();
  const summaryRequest = page.waitForRequest((pending) => (
    pending.method() === "POST" && pending.url().endsWith(`/target-roles/${role.id}/summary`)
  ));
  await page.getByRole("button", { name: "综合分析选中岗位" }).click();

  expect((await summaryRequest).postDataJSON()).toEqual({ job_ids: [jobs[0].id, jobs[2].id] });
  await expect(page.getByRole("heading", { name: "选中岗位综合分析" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "SQL", exact: true })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Excel", exact: true })).toHaveCount(0);
  await expect(page.getByText("100%", { exact: true })).toBeVisible();
});

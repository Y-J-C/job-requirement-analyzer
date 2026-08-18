import { expect, test } from "@playwright/test";

import { createTargetRole, taggedName } from "../support/api";


test("共享页头和移动端布局覆盖主要页面", async ({ page, request }) => {
  const role = await createTargetRole(request, taggedName("界面一致性"));
  await page.setViewportSize({ width: 390, height: 844 });

  for (const path of ["/", `/target-roles/${role.id}`, `/target-roles/${role.id}/summary`]) {
    await page.goto(path);
    await expect(page.getByRole("link", { name: "岗位门槛分析系统首页" })).toBeVisible();
    await expect(page.getByRole("button", { name: "退出登录" })).toHaveCount(0);
    await expect(page.locator("main")).toBeVisible();
    expect(await page.evaluate(() => (
      document.documentElement.scrollWidth <= document.documentElement.clientWidth
    ))).toBe(true);
  }
});

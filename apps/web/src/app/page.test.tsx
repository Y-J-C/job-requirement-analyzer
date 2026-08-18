import { render, screen } from "@testing-library/react";

import Home from "./page";


describe("Home", () => {
  it("presents the product workflow and keeps developer endpoints secondary", () => {
    render(<Home />);

    expect(
      screen.getByRole("heading", { level: 1, name: "岗位门槛分析系统" }),
    ).toBeTruthy();
    expect(screen.getByText("从岗位原文到可核验结论")).toBeTruthy();
    expect(screen.getByRole("list", { name: "使用流程" }).textContent).toContain("创建方向");
    expect(screen.getByRole("list", { name: "使用流程" }).textContent).toContain("综合分析");
    expect(screen.getByText(/DeepSeek 提取结果需经人工确认/)).toBeTruthy();
    expect(
      screen.getByRole("link", { name: "API 存活检查" }).getAttribute("href"),
    ).toBe("http://localhost:8000/health");
    expect(screen.getByRole("link", { name: "API 文档" }).getAttribute("href")).toBe(
      "http://localhost:8000/docs",
    );
  });
});

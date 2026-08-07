import { render, screen } from "@testing-library/react";

import Home from "./page";


describe("Home", () => {
  it("presents the project foundation and health endpoints", () => {
    render(<Home />);

    expect(
      screen.getByRole("heading", { level: 1, name: "岗位门槛分析系统" }),
    ).toBeTruthy();
    expect(screen.getByText("持久化分析 · 第六阶段")).toBeTruthy();
    expect(
      screen.getByRole("link", { name: "API 存活检查" }).getAttribute("href"),
    ).toBe("http://localhost:8000/health");
    expect(screen.getByRole("link", { name: "API 文档" }).getAttribute("href")).toBe(
      "http://localhost:8000/docs",
    );
  });
});

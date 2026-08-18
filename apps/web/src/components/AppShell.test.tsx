import { render, screen } from "@testing-library/react";

import { AppShell } from "./AppShell";


describe("AppShell", () => {
  it("renders shared navigation without a user session or login action", () => {
    render(<AppShell><p>页面内容</p></AppShell>);

    expect(screen.getByRole("link", { name: /岗位门槛/ }).getAttribute("href")).toBe("/");
    expect(screen.getByRole("navigation", { name: "全局导航" })).toBeTruthy();
    expect(screen.queryByRole("button", { name: "退出登录" })).toBeNull();
    expect(screen.queryByText("local-user")).toBeNull();
    expect(screen.getByText("页面内容")).toBeTruthy();
  });
});

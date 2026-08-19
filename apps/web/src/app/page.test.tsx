import { render, screen } from "@testing-library/react";

import Home from "./page";


describe("Home", () => {
  it("puts direction actions first without developer-only details", () => {
    render(<Home />);

    expect(screen.getByRole("heading", { level: 1, name: "方向总览" })).toBeTruthy();
    expect(screen.getByRole("button", { name: "新建方向" })).toBeTruthy();
    expect(screen.getByRole("heading", { level: 2, name: "已有方向" })).toBeTruthy();
    expect(screen.queryByText(/DeepSeek 提取结果/)).toBeNull();
    expect(screen.queryByRole("link", { name: "API 文档" })).toBeNull();
  });
});

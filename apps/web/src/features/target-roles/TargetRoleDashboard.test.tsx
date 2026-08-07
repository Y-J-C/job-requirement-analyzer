import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { TargetRoleDashboard } from "./TargetRoleDashboard";


function jsonResponse(body: unknown, ok = true): Response {
  return {
    ok,
    json: async () => body,
  } as Response;
}


afterEach(() => {
  vi.unstubAllGlobals();
});


describe("TargetRoleDashboard", () => {
  it("shows an empty state and creates the first target role", async () => {
    const createdRole = {
      id: "87c8a337-f85d-4d17-8dd4-da998636e3d7",
      name: "数据分析实习生",
      recruitment_stage: "daily_internship",
      description: "关注互联网公司的数据岗位",
      created_at: "2026-08-06T12:00:00Z",
      updated_at: "2026-08-06T12:00:00Z",
      job_count: 0,
    };
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(jsonResponse({ items: [], total: 0 }))
      .mockResolvedValueOnce(jsonResponse(createdRole));
    vi.stubGlobal("fetch", fetchMock);

    render(<TargetRoleDashboard />);

    expect(await screen.findByText("还没有目标岗位方向")).toBeTruthy();

    fireEvent.change(screen.getByLabelText("方向名称"), {
      target: { value: "数据分析实习生" },
    });
    fireEvent.change(screen.getByLabelText("招聘阶段"), {
      target: { value: "daily_internship" },
    });
    fireEvent.change(screen.getByLabelText("说明（可选）"), {
      target: { value: "关注互联网公司的数据岗位" },
    });
    fireEvent.click(screen.getByRole("button", { name: "创建目标方向" }));

    const roleHeading = await screen.findByRole("heading", { name: "数据分析实习生" });
    const roleItem = roleHeading.closest("li");
    expect(roleItem).not.toBeNull();
    expect(within(roleItem as HTMLLIElement).getByText("日常实习")).toBeTruthy();
    expect(fetchMock).toHaveBeenCalledTimes(2);

    const createRequest = fetchMock.mock.calls[1];
    expect(createRequest[0]).toBe("http://localhost:8000/api/v1/target-roles");
    expect(JSON.parse(createRequest[1].body)).toEqual({
      name: "数据分析实习生",
      recruitment_stage: "daily_internship",
      description: "关注互联网公司的数据岗位",
    });
  });

  it("shows a retryable error when loading fails", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(jsonResponse({ detail: "unavailable" }, false))
      .mockResolvedValueOnce(jsonResponse({ items: [], total: 0 }));
    vi.stubGlobal("fetch", fetchMock);

    render(<TargetRoleDashboard />);

    expect(await screen.findByText("目标方向加载失败，请重试。")).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: "重新加载" }));

    await waitFor(() => {
      expect(screen.getByText("还没有目标岗位方向")).toBeTruthy();
    });
  });
});

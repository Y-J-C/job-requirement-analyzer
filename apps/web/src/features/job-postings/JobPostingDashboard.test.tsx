import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { JobPostingDashboard } from "./JobPostingDashboard";


function jsonResponse(body: unknown, ok = true): Response {
  return { ok, json: async () => body } as Response;
}


const role = {
  id: "87c8a337-f85d-4d17-8dd4-da998636e3d7",
  name: "数据分析实习生",
  recruitment_stage: "daily_internship",
  description: null,
  created_at: "2026-08-06T12:00:00Z",
  updated_at: "2026-08-06T12:00:00Z",
  job_count: 0,
};

const job = {
  id: "f88812df-e516-4fb9-a0d0-69776d15b214",
  target_role_id: role.id,
  company_name: "示例科技",
  job_title: "数据分析实习生",
  recruitment_stage: "daily_internship",
  city: "上海",
  source_url: "https://example.com/jobs/1",
  original_text: "负责业务数据分析，要求熟练使用 SQL。",
  status: "draft",
  collected_at: "2026-08-06T12:00:00Z",
  created_at: "2026-08-06T12:00:00Z",
  updated_at: "2026-08-06T12:00:00Z",
};


afterEach(() => {
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});


describe("JobPostingDashboard", () => {
  it("creates a job and renders the preserved JD text", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(jsonResponse(role))
      .mockResolvedValueOnce(jsonResponse({ items: [], total: 0 }))
      .mockResolvedValueOnce(jsonResponse(job));
    vi.stubGlobal("fetch", fetchMock);

    render(<JobPostingDashboard roleId={role.id} />);

    expect(await screen.findByRole("heading", { name: role.name })).toBeTruthy();
    expect(screen.getByText("还没有录入岗位")).toBeTruthy();

    fireEvent.change(screen.getByLabelText("公司名称"), {
      target: { value: "示例科技" },
    });
    fireEvent.change(screen.getByLabelText("岗位名称"), {
      target: { value: "数据分析实习生" },
    });
    fireEvent.change(screen.getByLabelText("城市（可选）"), {
      target: { value: "上海" },
    });
    fireEvent.change(screen.getByLabelText("来源 URL（可选）"), {
      target: { value: "https://example.com/jobs/1" },
    });
    fireEvent.change(screen.getByLabelText("JD 原文"), {
      target: { value: job.original_text },
    });
    fireEvent.click(screen.getByRole("button", { name: "保存岗位" }));

    expect(await screen.findByRole("heading", { name: "示例科技 · 数据分析实习生" })).toBeTruthy();
    expect(screen.getByText(job.original_text)).toBeTruthy();
    expect(fetchMock).toHaveBeenCalledTimes(3);
  });

  it("requires confirmation before deleting a job", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(jsonResponse({ ...role, job_count: 1 }))
      .mockResolvedValueOnce(jsonResponse({ items: [job], total: 1 }))
      .mockResolvedValueOnce(jsonResponse(null));
    vi.stubGlobal("fetch", fetchMock);
    const confirmMock = vi.spyOn(window, "confirm").mockReturnValueOnce(false).mockReturnValueOnce(true);

    render(<JobPostingDashboard roleId={role.id} />);
    const deleteButton = await screen.findByRole("button", { name: "删除岗位" });

    fireEvent.click(deleteButton);
    expect(confirmMock).toHaveBeenCalledTimes(1);
    expect(fetchMock).toHaveBeenCalledTimes(2);

    fireEvent.click(deleteButton);
    await waitFor(() => {
      expect(screen.queryByText(job.original_text)).toBeNull();
    });
    expect(fetchMock).toHaveBeenCalledTimes(3);
  });
});


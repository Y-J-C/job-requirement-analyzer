import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { RequirementReviewDashboard } from "./RequirementReviewDashboard";


function jsonResponse(body: unknown, ok = true): Response {
  return new Response(JSON.stringify(body), {
    status: ok ? 200 : 503,
    headers: { "Content-Type": "application/json" },
  });
}


const job = {
  id: "f88812df-e516-4fb9-a0d0-69776d15b214",
  active_analysis_run_id: null,
  target_role_id: "87c8a337-f85d-4d17-8dd4-da998636e3d7",
  company_name: "示例科技",
  job_title: "数据分析实习生",
  recruitment_stage: "daily_internship",
  city: "上海",
  source_url: null,
  original_text: "熟练使用 SQL，有数据分析项目经验者优先。",
  status: "draft",
  collected_at: "2026-08-06T12:00:00Z",
  created_at: "2026-08-06T12:00:00Z",
  updated_at: "2026-08-06T12:00:00Z",
};

const requirement = {
  id: "68df1a89-816f-4b2c-92c6-2627e75381f9",
  analysis_run_id: "4c55ac86-563b-43ad-9574-9c984a81d392",
  original_text: "熟练使用 SQL",
  normalized_name: "SQL",
  requirement_type: "core_competency",
  explicitness: "explicit",
  confidence: null,
  user_confirmed: false,
  user_modified: true,
  created_at: "2026-08-06T12:00:00Z",
  updated_at: "2026-08-06T12:00:00Z",
};


afterEach(() => {
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});


describe("RequirementReviewDashboard", () => {
  it("starts AI analysis and shows extracted requirements after completion", async () => {
    const aiRequirement = {
      ...requirement,
      confidence: "0.9800",
      user_modified: false,
    };
    const run = {
      id: "77334d69-c46e-4dce-a42d-7d9a2dd58fb5",
      job_posting_id: job.id,
      version: 1,
      status: "pending",
      source: "ai",
      model_provider: "deepseek",
      model_name: "deepseek-v4-flash",
      prompt_version: "requirements-v1",
      schema_version: "1.0",
      error_code: null,
      attempt_count: 0,
      max_attempts: 3,
      available_at: "2026-08-06T12:00:00Z",
      lease_expires_at: null,
      started_at: null,
      completed_at: null,
      created_at: "2026-08-06T12:00:00Z",
      updated_at: "2026-08-06T12:00:00Z",
    };
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(jsonResponse(job))
      .mockResolvedValueOnce(jsonResponse({ items: [], total: 0, job_status: "draft" }))
      .mockResolvedValueOnce(jsonResponse(run))
      .mockResolvedValueOnce(jsonResponse({ ...run, status: "succeeded" }))
      .mockResolvedValueOnce(jsonResponse({ ...job, status: "review_required" }))
      .mockResolvedValueOnce(
        jsonResponse({ items: [aiRequirement], total: 1, job_status: "review_required" }),
      );
    vi.stubGlobal("fetch", fetchMock);

    render(<RequirementReviewDashboard jobId={job.id} />);
    fireEvent.click(await screen.findByRole("button", { name: "使用 DeepSeek 提取门槛" }));

    expect(await screen.findByRole("heading", { name: "SQL" })).toBeTruthy();
    expect(screen.getByText("AI 提取 · 置信度 98%" )).toBeTruthy();
    const analyzeRequest = fetchMock.mock.calls
      .map(([input]) => input as Request)
      .find((request) => request.url.endsWith(`/api/v1/jobs/${job.id}/analyze`));
    expect(analyzeRequest?.method).toBe("POST");
  });

  it("guides manual review when AI analysis finds no requirements", async () => {
    const run = {
      id: "77334d69-c46e-4dce-a42d-7d9a2dd58fb5",
      job_posting_id: job.id,
      version: 1,
      status: "pending",
      source: "ai",
      model_provider: "deepseek",
      model_name: "deepseek-v4-flash",
      prompt_version: "requirements-v2",
      schema_version: "1.0",
      error_code: null,
      attempt_count: 0,
      max_attempts: 3,
      available_at: "2026-08-06T12:00:00Z",
      lease_expires_at: null,
      started_at: null,
      completed_at: null,
      created_at: "2026-08-06T12:00:00Z",
      updated_at: "2026-08-06T12:00:00Z",
    };
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(jsonResponse(job))
      .mockResolvedValueOnce(jsonResponse({ items: [], total: 0, job_status: "draft" }))
      .mockResolvedValueOnce(jsonResponse(run))
      .mockResolvedValueOnce(jsonResponse({ ...run, status: "succeeded" }))
      .mockResolvedValueOnce(jsonResponse({ ...job, status: "review_required" }))
      .mockResolvedValueOnce(
        jsonResponse({ items: [], total: 0, job_status: "review_required" }),
      );
    vi.stubGlobal("fetch", fetchMock);

    render(<RequirementReviewDashboard jobId={job.id} />);
    fireEvent.click(await screen.findByRole("button", { name: "使用 DeepSeek 提取门槛" }));

    expect(await screen.findByText(
      "未提取到明确要求，请核对原文并手工新增。",
      { exact: true },
    )).toBeTruthy();
    expect(screen.queryByText("AI 提取失败，未写入不完整结果。请稍后重试。")).toBeNull();
    expect(
      (screen.getByRole("button", { name: "确认整份岗位" }) as HTMLButtonElement).disabled,
    ).toBe(true);
    expect(screen.getByRole("heading", { name: "新增原子要求" })).toBeTruthy();
  });

  it("restores the empty analysis guidance after refresh", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(jsonResponse({ ...job, status: "review_required" }))
      .mockResolvedValueOnce(
        jsonResponse({ items: [], total: 0, job_status: "review_required" }),
      );
    vi.stubGlobal("fetch", fetchMock);

    render(<RequirementReviewDashboard jobId={job.id} />);

    expect(await screen.findByText(
      "未提取到明确要求，请核对原文并手工新增。",
      { exact: true },
    )).toBeTruthy();
  });

  it("shows the source JD and creates a manual requirement", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(jsonResponse(job))
      .mockResolvedValueOnce(jsonResponse({ items: [], total: 0, job_status: "draft" }))
      .mockResolvedValueOnce(jsonResponse(requirement));
    vi.stubGlobal("fetch", fetchMock);

    render(<RequirementReviewDashboard jobId={job.id} />);

    expect(await screen.findByRole("heading", { name: "示例科技 · 数据分析实习生" })).toBeTruthy();
    expect(screen.getByText(job.original_text)).toBeTruthy();
    expect(screen.getByText("还没有门槛条目")).toBeTruthy();

    fireEvent.change(screen.getByLabelText("标准条件名称"), {
      target: { value: "SQL" },
    });
    fireEvent.change(screen.getByLabelText("原文依据"), {
      target: { value: "熟练使用 SQL" },
    });
    fireEvent.click(screen.getByRole("button", { name: "新增门槛" }));

    expect(await screen.findByRole("heading", { name: "SQL" })).toBeTruthy();
    expect(screen.getAllByText("待确认").length).toBeGreaterThan(0);
    expect(fetchMock).toHaveBeenCalledTimes(3);
  });

  it("edits an item and confirms the entire job", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(jsonResponse({ ...job, status: "review_required" }))
      .mockResolvedValueOnce(
        jsonResponse({ items: [requirement], total: 1, job_status: "review_required" }),
      )
      .mockResolvedValueOnce(
        jsonResponse({ ...requirement, normalized_name: "SQL 查询" }),
      )
      .mockResolvedValueOnce(jsonResponse({ ...job, status: "confirmed" }));
    vi.stubGlobal("fetch", fetchMock);
    const confirmMock = vi.spyOn(window, "confirm").mockReturnValueOnce(false).mockReturnValueOnce(true);

    render(<RequirementReviewDashboard jobId={job.id} />);

    fireEvent.click(await screen.findByRole("button", { name: "编辑 SQL" }));
    const editName = screen.getByLabelText("编辑标准条件名称");
    fireEvent.change(editName, { target: { value: "SQL 查询" } });
    fireEvent.click(screen.getByRole("button", { name: "保存修改" }));

    expect(await screen.findByRole("heading", { name: "SQL 查询" })).toBeTruthy();

    const confirmButton = screen.getByRole("button", { name: "确认整份岗位" });
    fireEvent.click(confirmButton);
    expect(fetchMock).toHaveBeenCalledTimes(3);
    fireEvent.click(confirmButton);

    await waitFor(() => expect(screen.getAllByText("已确认").length).toBe(2));
    expect(confirmMock).toHaveBeenCalledTimes(2);
    expect(fetchMock).toHaveBeenCalledTimes(4);
  });

  it("requires confirmation before deleting an unconfirmed item", async () => {
    const unconfirmedRequirement = { ...requirement, user_confirmed: false };
    const secondRequirement = {
      ...unconfirmedRequirement,
      id: "c4fdd80f-509b-4fa4-b758-e0522f8d6f19",
      normalized_name: "数据分析项目经验",
      requirement_type: "preferred",
      original_text: "数据分析项目经验者优先",
    };
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(jsonResponse({ ...job, status: "review_required" }))
      .mockResolvedValueOnce(
        jsonResponse({
          items: [unconfirmedRequirement, secondRequirement],
          total: 2,
          job_status: "review_required",
        }),
      )
      .mockResolvedValueOnce(jsonResponse(null));
    vi.stubGlobal("fetch", fetchMock);
    const confirmMock = vi.spyOn(window, "confirm").mockReturnValueOnce(false).mockReturnValueOnce(true);

    render(<RequirementReviewDashboard jobId={job.id} />);
    const deleteButton = await screen.findByRole("button", { name: "删除 SQL" });

    fireEvent.click(deleteButton);
    expect(fetchMock).toHaveBeenCalledTimes(2);
    fireEvent.click(deleteButton);

    await waitFor(() => expect(screen.queryByRole("heading", { name: "SQL" })).toBeNull());
    expect(screen.getByRole("heading", { name: "数据分析项目经验" })).toBeTruthy();
    expect(screen.getAllByText("待确认").length).toBeGreaterThan(0);
    expect(screen.queryByText("已确认")).toBeNull();
    expect(confirmMock).toHaveBeenCalledTimes(2);
    expect(fetchMock).toHaveBeenCalledTimes(3);
  });

  it("keeps the active confirmed version read-only", async () => {
    const activeJob = {
      ...job,
      active_analysis_run_id: requirement.analysis_run_id,
      status: "confirmed",
    };
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(jsonResponse(activeJob))
      .mockResolvedValueOnce(jsonResponse({
        items: [{ ...requirement, user_confirmed: true }],
        total: 1,
        job_status: "confirmed",
      }));
    vi.stubGlobal("fetch", fetchMock);

    render(<RequirementReviewDashboard jobId={job.id} />);

    expect(await screen.findByText("当前为已生效版本。如需变更，请重新分析并确认新版本。")).toBeTruthy();
    expect(screen.queryByRole("button", { name: "编辑 SQL" })).toBeNull();
    expect(screen.queryByRole("button", { name: "删除 SQL" })).toBeNull();
    expect(screen.getByRole("button", { name: "使用 DeepSeek 重新分析" })).toBeTruthy();
  });

  it("recovers polling after refreshing a queued job", async () => {
    const run = {
      id: "77334d69-c46e-4dce-a42d-7d9a2dd58fb5",
      job_posting_id: job.id,
      version: 1,
      status: "pending",
      source: "ai",
      model_provider: "deepseek",
      model_name: "deepseek-v4-flash",
      prompt_version: "requirements-v1",
      schema_version: "1.0",
      error_code: null,
      attempt_count: 0,
      max_attempts: 3,
      available_at: "2026-08-06T12:00:00Z",
      lease_expires_at: null,
      started_at: null,
      completed_at: null,
      created_at: "2026-08-06T12:00:00Z",
      updated_at: "2026-08-06T12:00:00Z",
    };
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(jsonResponse({ ...job, status: "queued" }))
      .mockResolvedValueOnce(jsonResponse({ items: [], total: 0, job_status: "queued" }))
      .mockResolvedValueOnce(jsonResponse(run))
      .mockResolvedValueOnce(jsonResponse({ ...run, status: "succeeded" }))
      .mockResolvedValueOnce(jsonResponse({ ...job, status: "review_required" }))
      .mockResolvedValueOnce(jsonResponse({ items: [requirement], total: 1, job_status: "review_required" }));
    vi.stubGlobal("fetch", fetchMock);

    render(<RequirementReviewDashboard jobId={job.id} />);

    expect(await screen.findByRole("heading", { name: "SQL" })).toBeTruthy();
    expect(fetchMock.mock.calls.some(([input]) =>
      (input as Request).url.endsWith(`/api/v1/jobs/${job.id}/analysis-runs/latest`)
    )).toBe(true);
  });
});

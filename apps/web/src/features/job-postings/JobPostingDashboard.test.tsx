import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { JobPostingDashboard } from "./JobPostingDashboard";


function jsonResponse(body: unknown, ok = true): Response {
  return new Response(JSON.stringify(body), {
    status: ok ? 200 : 503,
    headers: { "Content-Type": "application/json" },
  });
}

function requestDetails(input: string | URL | Request, init?: RequestInit) {
  const request = input instanceof Request ? input : new Request(input, init);
  return { request, url: request.url, method: request.method };
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
  active_analysis_run_id: null,
  target_role_id: role.id,
  company_name: "示例科技",
  job_title: "数据分析实习生",
  recruitment_stage: "daily_internship",
  city: "上海",
  source_url: "https://example.com/jobs/1",
  original_text: "负责业务数据分析，要求熟练使用 SQL。",
  status: "queued",
  collected_at: "2026-08-06T12:00:00Z",
  created_at: "2026-08-06T12:00:00Z",
  updated_at: "2026-08-06T12:00:00Z",
};

const sourceFile = {
  id: "4f04775f-40c1-481e-9bc4-81b113242a6a",
  job_posting_id: job.id,
  sequence_index: 0,
  original_filename: "岗位.md",
  declared_mime_type: "text/markdown",
  detected_media_type: "text/markdown",
  size_bytes: 17,
  sha256: "a".repeat(64),
  parse_status: "failed",
  parser_version: null,
  error_code: "no_extractable_text",
  created_at: "2026-08-08T02:00:00Z",
  updated_at: "2026-08-08T02:00:00Z",
};

afterEach(() => {
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

function mockInitialJobs(items: unknown[]) {
  return vi.fn(async (input: string | URL | Request, init?: RequestInit) => {
    const { method, url } = requestDetails(input, init);
    if (url.includes("/target-roles/") && url.includes("/jobs?") && method === "GET") {
      return jsonResponse({ items, total: items.length });
    }
    if (url.endsWith(`/target-roles/${role.id}`)) return jsonResponse(role);
    throw new Error(`Unexpected request: ${method} ${url}`);
  });
}

describe("JobPostingDashboard", () => {
  it("submits text once and immediately renders the queued job", async () => {
    const fetchMock = mockInitialJobs([]);
    fetchMock.mockImplementation(async (input: string | URL | Request, init?: RequestInit) => {
      const { method, url } = requestDetails(input, init);
      if (method === "POST" && url.endsWith("/jobs/intake")) {
        return jsonResponse({
          job,
          source_files: [],
          analysis_run: { id: "run-1", version: 1, status: "pending" },
        });
      }
      if (url.includes("/jobs?") && method === "GET") return jsonResponse({ items: [], total: 0 });
      if (url.endsWith(`/target-roles/${role.id}`)) return jsonResponse(role);
      if (url.endsWith(`/jobs/${job.id}`)) return jsonResponse({ ...job, status: "review_required" });
      throw new Error(`Unexpected request: ${url}`);
    });
    vi.stubGlobal("fetch", fetchMock);

    render(<JobPostingDashboard roleId={role.id} />);
    expect(await screen.findByRole("heading", { name: role.name })).toBeTruthy();
    expect(screen.getByText("01 / 录入")).toBeTruthy();
    expect(screen.getByText("02 / 岗位记录")).toBeTruthy();
    fireEvent.change(screen.getByLabelText("公司名称（可选提示）"), { target: { value: "示例科技" } });
    fireEvent.change(screen.getByLabelText("岗位名称（可选提示）"), { target: { value: "数据分析实习生" } });
    fireEvent.change(screen.getByLabelText("岗位原文"), { target: { value: job.original_text } });
    fireEvent.submit(screen.getByRole("button", { name: "提交并自动分析" }).closest("form")!);

    expect(await screen.findByRole("heading", { name: "示例科技 · 数据分析实习生" })).toBeTruthy();
    const intakeCall = fetchMock.mock.calls.find(([input, init]) =>
      requestDetails(input, init).method === "POST"
    );
    const intakeBody = await requestDetails(intakeCall![0], intakeCall![1]).request.clone().formData();
    expect(intakeBody.get("source_type")).toBe("text");
  });

  it("keeps selected image order in multipart intake", async () => {
    const queuedImageJob = { ...job, status: "extracting", original_text: "" };
    const fetchMock = vi.fn(async (input: string | URL | Request, init?: RequestInit) => {
      const { method, url } = requestDetails(input, init);
      if (url.includes("/jobs?") && method === "GET") return jsonResponse({ items: [], total: 0 });
      if (url.endsWith(`/target-roles/${role.id}`)) return jsonResponse(role);
      if (method === "POST" && url.endsWith("/jobs/intake")) {
        return jsonResponse({ job: queuedImageJob, source_files: [], analysis_run: null });
      }
      if (url.endsWith(`/jobs/${job.id}`)) return jsonResponse({ ...job, status: "review_required" });
      if (url.endsWith(`/jobs/${job.id}/source-file`)) return jsonResponse(sourceFile);
      throw new Error(`Unexpected request: ${url}`);
    });
    vi.stubGlobal("fetch", fetchMock);

    render(<JobPostingDashboard roleId={role.id} />);
    expect(await screen.findByRole("heading", { name: role.name })).toBeTruthy();
    fireEvent.click(screen.getByLabelText("上传图片"));
    const first = new File(["first"], "第一页.png", { type: "image/png" });
    const second = new File(["second"], "第二页.png", { type: "image/png" });
    fireEvent.change(screen.getByLabelText("岗位图片"), { target: { files: [first, second] } });
    expect(screen.getByRole("list", { name: "图片处理顺序" }).textContent).toContain("第一页.png");
    const appendSpy = vi.spyOn(FormData.prototype, "append");
    fireEvent.submit(screen.getByRole("button", { name: "提交并自动分析" }).closest("form")!);

    await waitFor(() => expect(fetchMock.mock.calls.some(([input, init]) =>
      requestDetails(input, init).method === "POST"
    )).toBe(true));
    const files = appendSpy.mock.calls
      .filter(([name]) => name === "files")
      .map(([, value]) => (value as File).name);
    expect(files).toEqual(["第一页.png", "第二页.png"]);
  });

  it("restores a stable extraction error and offers retry", async () => {
    const failedJob = { ...job, status: "failed", original_text: "" };
    const fetchMock = vi.fn(async (input: string | URL | Request) => {
      const { url } = requestDetails(input);
      if (url.includes("/jobs?")) return jsonResponse({ items: [failedJob], total: 1 });
      if (url.endsWith(`/target-roles/${role.id}`)) return jsonResponse(role);
      if (url.endsWith(`/jobs/${job.id}/source-file`)) return jsonResponse(sourceFile);
      throw new Error(`Unexpected request: ${url}`);
    });
    vi.stubGlobal("fetch", fetchMock);

    render(<JobPostingDashboard roleId={role.id} />);

    expect(await screen.findByText("未检测到可解析文本，请换用更清晰的图片或文件。")).toBeTruthy();
    expect(screen.getByRole("button", { name: "重试处理" })).toBeTruthy();
  });

  it("selects arbitrary confirmed jobs and submits only those ids", async () => {
    const confirmed = (id: string, company: string) => ({
      ...job,
      id,
      company_name: company,
      status: "confirmed",
      active_analysis_run_id: `run-${id}`,
    });
    const first = confirmed("job-1", "甲公司");
    const second = confirmed("job-2", "乙公司");
    const third = confirmed("job-3", "丙公司");
    const fetchMock = vi.fn(async (input: string | URL | Request, init?: RequestInit) => {
      const { method, url } = requestDetails(input, init);
      if (url.includes("/jobs?") && method === "GET") return jsonResponse({ items: [first, second, third], total: 3 });
      if (url.endsWith(`/target-roles/${role.id}`)) return jsonResponse(role);
      if (method === "POST" && url.endsWith("/summary")) {
        return jsonResponse({
          target_role_id: role.id,
          target_role_name: role.name,
          sample_job_count: 2,
          confirmed_job_count: 2,
          sample_size_notice: "样本量很小，仅供查看录入结果。",
          selected_job_ids: [first.id, third.id],
          items: [],
        });
      }
      throw new Error(`Unexpected request: ${url}`);
    });
    vi.stubGlobal("fetch", fetchMock);

    render(<JobPostingDashboard roleId={role.id} />);
    await screen.findByRole("heading", { name: "甲公司 · 数据分析实习生" });
    fireEvent.click(screen.getByLabelText("选择 甲公司 · 数据分析实习生"));
    fireEvent.click(screen.getByLabelText("选择 丙公司 · 数据分析实习生"));
    fireEvent.click(screen.getByRole("button", { name: "综合分析选中岗位" }));

    expect(await screen.findByRole("heading", { name: "选中岗位综合分析" })).toBeTruthy();
    const summaryCall = fetchMock.mock.calls.find(([input, init]) =>
      requestDetails(input, init).method === "POST"
    );
    expect(await requestDetails(summaryCall![0], summaryCall![1]).request.clone().json()).toEqual({
      job_ids: [first.id, third.id],
    });
  });

  it("filters visible jobs while preserving selections across searches", async () => {
    const confirmed = (id: string, company: string) => ({
      ...job,
      id,
      company_name: company,
      status: "confirmed",
      active_analysis_run_id: `run-${id}`,
    });
    const first = confirmed("job-1", "甲公司");
    const second = { ...job, id: "job-2", company_name: "乙公司", status: "review_required" };
    const third = confirmed("job-3", "丙公司");
    vi.stubGlobal("fetch", mockInitialJobs([first, second, third]));

    render(<JobPostingDashboard roleId={role.id} />);
    await screen.findByRole("heading", { name: "甲公司 · 数据分析实习生" });

    fireEvent.change(screen.getByLabelText("搜索岗位"), { target: { value: "甲公司" } });
    expect(screen.getByText("显示 1 / 3 个岗位")).toBeTruthy();
    fireEvent.click(screen.getByLabelText("全选当前可汇总岗位"));
    expect((screen.getByLabelText("选择 甲公司 · 数据分析实习生") as HTMLInputElement).checked)
      .toBe(true);

    fireEvent.change(screen.getByLabelText("搜索岗位"), { target: { value: "丙公司" } });
    expect(screen.queryByRole("heading", { name: "甲公司 · 数据分析实习生" })).toBeNull();
    fireEvent.click(screen.getByLabelText("全选当前可汇总岗位"));
    expect(screen.getByText("已选 2 / 2")).toBeTruthy();

    fireEvent.change(screen.getByLabelText("搜索岗位"), { target: { value: "不存在" } });
    expect(screen.getByText("没有匹配的岗位")).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: "清除筛选" }));
    expect(screen.getByRole("heading", { name: "甲公司 · 数据分析实习生" })).toBeTruthy();
  });
});

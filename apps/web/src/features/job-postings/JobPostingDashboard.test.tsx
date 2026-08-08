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

const extractingJob = {
  ...job,
  id: "5f4ebd38-7933-4bc2-b7c7-109f0777b94a",
  original_text: "",
  status: "extracting",
};

const sourceFile = {
  id: "4f04775f-40c1-481e-9bc4-81b113242a6a",
  job_posting_id: extractingJob.id,
  original_filename: "岗位.md",
  declared_mime_type: "text/markdown",
  detected_media_type: "text/markdown",
  size_bytes: 17,
  sha256: "a".repeat(64),
  parse_status: "pending",
  parser_version: null,
  error_code: null,
  created_at: "2026-08-08T02:00:00Z",
  updated_at: "2026-08-08T02:00:00Z",
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

  it("uploads a source file and refreshes the extracted text", async () => {
    const extractedJob = { ...extractingJob, original_text: "# JD\nSQL required", status: "draft" };
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(jsonResponse(role))
      .mockResolvedValueOnce(jsonResponse({ items: [], total: 0 }))
      .mockResolvedValueOnce(jsonResponse({ job: extractingJob, source_file: sourceFile }))
      .mockResolvedValueOnce(jsonResponse(extractedJob))
      .mockResolvedValueOnce(jsonResponse({
        ...sourceFile,
        parse_status: "succeeded",
        parser_version: "document-parser-v1",
      }));
    vi.stubGlobal("fetch", fetchMock);

    render(<JobPostingDashboard roleId={role.id} />);
    expect(await screen.findByRole("heading", { name: role.name })).toBeTruthy();

    fireEvent.click(screen.getByLabelText("上传文件"));
    expect(screen.queryByLabelText("JD 原文")).toBeNull();
    expect(screen.getByText("支持 PDF、Markdown、DOCX；最大 10 MiB")).toBeTruthy();
    fireEvent.change(screen.getByLabelText("公司名称"), {
      target: { value: "示例科技" },
    });
    fireEvent.change(screen.getByLabelText("岗位名称"), {
      target: { value: "数据分析实习生" },
    });
    const file = new File(["# JD\nSQL required"], "岗位.md", { type: "text/markdown" });
    fireEvent.change(screen.getByLabelText("岗位文件"), { target: { files: [file] } });
    const submitButton = screen.getByRole("button", { name: "上传并提取" });
    fireEvent.submit(submitButton.closest("form")!);

    expect(await screen.findByText(/SQL required/)).toBeTruthy();
    const uploadCall = fetchMock.mock.calls[2];
    expect(uploadCall[1].body).toBeInstanceOf(FormData);
    expect(uploadCall[1].headers).toBeUndefined();
  });

  it("restores a stable parse error after page refresh", async () => {
    const failedJob = { ...extractingJob, status: "failed" };
    const failedSource = {
      ...sourceFile,
      parse_status: "failed",
      error_code: "no_extractable_text",
    };
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(jsonResponse({ ...role, job_count: 1 }))
      .mockResolvedValueOnce(jsonResponse({ items: [failedJob], total: 1 }))
      .mockResolvedValueOnce(jsonResponse(failedJob))
      .mockResolvedValueOnce(jsonResponse(failedSource));
    vi.stubGlobal("fetch", fetchMock);

    render(<JobPostingDashboard roleId={role.id} />);

    expect(await screen.findByText("未检测到可解析文本；扫描版 PDF 暂不支持。")).toBeTruthy();
    expect(fetchMock).toHaveBeenCalledTimes(4);
  });

  it("shows a stable upload validation error in Chinese", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(jsonResponse(role))
      .mockResolvedValueOnce(jsonResponse({ items: [], total: 0 }))
      .mockResolvedValueOnce(jsonResponse({
        detail: { code: "file_signature_mismatch", message: "internal detail" },
      }, false));
    vi.stubGlobal("fetch", fetchMock);

    render(<JobPostingDashboard roleId={role.id} />);
    expect(await screen.findByRole("heading", { name: role.name })).toBeTruthy();
    fireEvent.click(screen.getByLabelText("上传文件"));
    fireEvent.change(screen.getByLabelText("公司名称"), { target: { value: "示例科技" } });
    fireEvent.change(screen.getByLabelText("岗位名称"), { target: { value: "数据分析" } });
    fireEvent.change(screen.getByLabelText("岗位文件"), {
      target: { files: [new File(["bad"], "岗位.pdf", { type: "application/pdf" })] },
    });
    fireEvent.submit(screen.getByRole("button", { name: "上传并提取" }).closest("form")!);

    expect((await screen.findByRole("alert")).textContent).toContain("文件内容与扩展名不匹配");
  });
});

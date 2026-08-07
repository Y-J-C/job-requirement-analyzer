import { fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { SummaryDashboard } from "./SummaryDashboard";


function jsonResponse(body: unknown, ok = true): Response {
  return { ok, json: async () => body } as Response;
}


const summary = {
  target_role_id: "87c8a337-f85d-4d17-8dd4-da998636e3d7",
  target_role_name: "数据分析实习生",
  sample_job_count: 3,
  confirmed_job_count: 2,
  sample_size_notice: "样本量很小，仅供查看录入结果。",
  items: [
    {
      normalized_name: "SQL",
      requirement_type: "core_competency",
      mentioning_job_count: 2,
      confirmed_job_count: 2,
      coverage_rate: 1,
      evidence_count: 3,
      explicit_evidence_count: 2,
      evidence: [
        {
          requirement_id: "68df1a89-816f-4b2c-92c6-2627e75381f9",
          job_id: "f88812df-e516-4fb9-a0d0-69776d15b214",
          company_name: "示例科技",
          job_title: "数据分析实习生",
          original_text: "熟练使用 SQL",
          explicitness: "explicit",
        },
        {
          requirement_id: "6c83f087-b0ed-411a-80af-155e4d26fe07",
          job_id: "3bf835f8-cde3-4172-acf3-b122b9b7fdd0",
          company_name: "样本公司",
          job_title: "商业分析实习生",
          original_text: "掌握 SQL 查询",
          explicitness: "implicit",
        },
        {
          requirement_id: "40fa947d-ab8e-438f-b117-22f60d7de2c8",
          job_id: "f88812df-e516-4fb9-a0d0-69776d15b214",
          company_name: "示例科技",
          job_title: "数据分析实习生",
          original_text: "能够编写复杂 SQL",
          explicitness: "explicit",
        },
      ],
    },
  ],
};


afterEach(() => {
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});


describe("SummaryDashboard", () => {
  it("renders metrics, coverage and traceable evidence", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValueOnce(jsonResponse(summary)));

    render(<SummaryDashboard roleId={summary.target_role_id} />);

    expect(await screen.findByRole("heading", { name: "数据分析实习生 · 确认汇总" })).toBeTruthy();
    const metrics = screen.getByRole("region", { name: "样本概况" });
    expect(metrics.textContent).toContain("3个全部样本");
    expect(metrics.textContent).toContain("2个已确认岗位");
    expect(screen.getByText(summary.sample_size_notice)).toBeTruthy();
    expect(screen.getByRole("heading", { name: "SQL" })).toBeTruthy();
    expect(screen.getByText("100%")).toBeTruthy();
    expect(screen.getByText("2 / 2 个岗位")).toBeTruthy();

    fireEvent.click(screen.getByText("查看 3 条原文证据"));
    expect(screen.getByText("熟练使用 SQL")).toBeTruthy();
    const evidenceLink = screen.getAllByRole("link", { name: "示例科技 · 数据分析实习生" })[0];
    expect(evidenceLink.getAttribute("href")).toBe("/jobs/f88812df-e516-4fb9-a0d0-69776d15b214/review");
  });

  it("refetches by category without changing the confirmed denominator", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(jsonResponse(summary))
      .mockResolvedValueOnce(jsonResponse({ ...summary, items: [] }));
    vi.stubGlobal("fetch", fetchMock);

    render(<SummaryDashboard roleId={summary.target_role_id} />);
    await screen.findByRole("heading", { name: "SQL" });

    fireEvent.change(screen.getByLabelText("要求类型筛选"), {
      target: { value: "preferred" },
    });

    expect(await screen.findByText("这个分类下还没有已确认要求")).toBeTruthy();
    expect(screen.getByRole("region", { name: "样本概况" }).textContent).toContain("2个已确认岗位");
    expect(fetchMock).toHaveBeenLastCalledWith(
      expect.stringContaining("requirement_type=preferred"),
      expect.anything(),
    );
  });

  it("shows an honest empty state when no job is confirmed", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValueOnce(jsonResponse({
      ...summary,
      confirmed_job_count: 0,
      items: [],
    })));

    render(<SummaryDashboard roleId={summary.target_role_id} />);

    expect(await screen.findByText("还没有已确认岗位")).toBeTruthy();
    expect(screen.queryByText("0%")).toBeNull();
  });
});

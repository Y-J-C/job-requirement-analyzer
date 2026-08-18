import { fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { SummaryExportButton } from "./SummaryExportButton";
import type { TargetRoleSummary } from "./types";


const summary: TargetRoleSummary = {
  target_role_id: "role-1",
  target_role_name: "数据分析实习生",
  sample_job_count: 1,
  confirmed_job_count: 1,
  sample_size_notice: "样本量很小。",
  selected_job_ids: [],
  items: [],
};


afterEach(() => {
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});


describe("SummaryExportButton", () => {
  it("downloads the current summary as a Markdown file", () => {
    const createObjectURL = vi.fn((blob: Blob) => {
      expect(blob).toBeInstanceOf(Blob);
      return "blob:summary-report";
    });
    const revokeObjectURL = vi.fn();
    vi.stubGlobal("URL", { createObjectURL, revokeObjectURL });
    const click = vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(() => undefined);

    render(<SummaryExportButton summary={summary} reportName="确认汇总" />);
    fireEvent.click(screen.getByRole("button", { name: "导出 Markdown" }));

    expect(createObjectURL).toHaveBeenCalledOnce();
    expect(createObjectURL.mock.calls[0][0]).toBeInstanceOf(Blob);
    expect(click).toHaveBeenCalledOnce();
    expect(revokeObjectURL).toHaveBeenCalledWith("blob:summary-report");
  });
});

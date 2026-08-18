import { describe, expect, it } from "vitest";

import { filterAndSortJobs } from "./jobPostingView";
import type { JobPosting } from "./types";


const baseJob: JobPosting = {
  id: "job-1",
  active_analysis_run_id: null,
  target_role_id: "role-1",
  company_name: "示例科技",
  job_title: "数据分析实习生",
  recruitment_stage: "daily_internship",
  city: "上海",
  source_url: null,
  original_text: "熟练使用 SQL",
  status: "review_required",
  collected_at: "2026-08-09T02:00:00Z",
  created_at: "2026-08-09T02:00:00Z",
  updated_at: "2026-08-09T02:00:00Z",
};


describe("filterAndSortJobs", () => {
  it("searches company, title and city without case sensitivity", () => {
    const jobs = [
      baseJob,
      { ...baseJob, id: "job-2", company_name: "Northwind AI", city: "北京" },
    ];

    expect(filterAndSortJobs(jobs, { query: " northWIND ", status: "all", sort: "newest" }))
      .toEqual([jobs[1]]);
    expect(filterAndSortJobs(jobs, { query: "上海", status: "all", sort: "newest" }))
      .toEqual([jobs[0]]);
  });

  it("groups active and review statuses into useful filters", () => {
    const jobs = [
      { ...baseJob, id: "queued", status: "queued" as const },
      { ...baseJob, id: "analyzing", status: "analyzing" as const },
      { ...baseJob, id: "draft", status: "draft" as const },
      { ...baseJob, id: "review", status: "review_required" as const },
      { ...baseJob, id: "confirmed", status: "confirmed" as const },
    ];

    expect(filterAndSortJobs(jobs, { query: "", status: "processing", sort: "newest" })
      .map((job) => job.id)).toEqual(["queued", "analyzing"]);
    expect(filterAndSortJobs(jobs, { query: "", status: "review", sort: "newest" })
      .map((job) => job.id)).toEqual(["draft", "review"]);
  });

  it("sorts by date or company without mutating the source list", () => {
    const jobs = [
      baseJob,
      { ...baseJob, id: "job-2", company_name: "阿尔法公司", created_at: "2026-08-08T02:00:00Z" },
    ];

    expect(filterAndSortJobs(jobs, { query: "", status: "all", sort: "oldest" })
      .map((job) => job.id)).toEqual(["job-2", "job-1"]);
    expect(filterAndSortJobs(jobs, { query: "", status: "all", sort: "company" })[0].company_name)
      .toBe("阿尔法公司");
    expect(jobs[0].id).toBe("job-1");
  });
});

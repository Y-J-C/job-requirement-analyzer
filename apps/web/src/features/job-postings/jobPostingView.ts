import type { JobPosting } from "./types";


export type JobStatusFilter = "all" | "processing" | "review" | "confirmed" | "failed";
export type JobSortOption = "newest" | "oldest" | "company";

export type JobViewOptions = {
  query: string;
  status: JobStatusFilter;
  sort: JobSortOption;
};

const processingStatuses = new Set<JobPosting["status"]>([
  "queued",
  "extracting",
  "analyzing",
]);

const reviewStatuses = new Set<JobPosting["status"]>(["draft", "review_required"]);


function matchesStatus(job: JobPosting, status: JobStatusFilter) {
  if (status === "all") return true;
  if (status === "processing") return processingStatuses.has(job.status);
  if (status === "review") return reviewStatuses.has(job.status);
  return job.status === status;
}


export function filterAndSortJobs(jobs: JobPosting[], options: JobViewOptions): JobPosting[] {
  const query = options.query.trim().toLocaleLowerCase("zh-CN");
  return jobs
    .filter((job) => {
      if (!matchesStatus(job, options.status)) return false;
      if (!query) return true;
      return [job.company_name, job.job_title, job.city]
        .filter((value): value is string => Boolean(value))
        .some((value) => value.toLocaleLowerCase("zh-CN").includes(query));
    })
    .sort((left, right) => {
      if (options.sort === "company") {
        return (left.company_name ?? "待补充公司")
          .localeCompare(right.company_name ?? "待补充公司", "zh-CN");
      }
      const direction = options.sort === "newest" ? -1 : 1;
      return left.created_at.localeCompare(right.created_at) * direction;
    });
}

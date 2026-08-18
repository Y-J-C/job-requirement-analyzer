import type { JobPosting } from "@/features/job-postings/types";
import { apiClient, requireData, requireSuccess } from "@/lib/api-client";

import type {
  AnalysisRun,
  RequirementInput,
  RequirementItem,
  RequirementListResponse,
} from "./types";


export async function fetchRequirements(jobId: string): Promise<RequirementListResponse> {
  return requireData(await apiClient.GET("/api/v1/jobs/{job_id}/requirements", {
    cache: "no-store",
    params: { path: { job_id: jobId } },
  }));
}


export async function createRequirement(
  jobId: string,
  input: RequirementInput,
): Promise<RequirementItem> {
  return requireData(await apiClient.POST("/api/v1/jobs/{job_id}/requirements", {
    params: { path: { job_id: jobId } },
    body: input,
  }));
}


export async function updateRequirement(
  requirementId: string,
  input: RequirementInput,
): Promise<RequirementItem> {
  return requireData(await apiClient.PATCH("/api/v1/requirements/{requirement_id}", {
    params: { path: { requirement_id: requirementId } },
    body: input,
  }));
}


export async function deleteRequirement(requirementId: string): Promise<void> {
  const result = await apiClient.DELETE("/api/v1/requirements/{requirement_id}", {
    params: { path: { requirement_id: requirementId } },
  });
  requireSuccess(result);
}


export async function confirmRequirements(jobId: string): Promise<JobPosting> {
  return requireData(await apiClient.POST("/api/v1/jobs/{job_id}/confirm-requirements", {
    params: { path: { job_id: jobId } },
  }));
}


export async function startAnalysis(jobId: string): Promise<AnalysisRun> {
  return requireData(await apiClient.POST("/api/v1/jobs/{job_id}/analyze", {
    params: { path: { job_id: jobId } },
  }));
}


export async function fetchAnalysisRun(runId: string): Promise<AnalysisRun> {
  return requireData(await apiClient.GET("/api/v1/analysis-runs/{run_id}", {
    cache: "no-store",
    params: { path: { run_id: runId } },
  }));
}


export async function fetchLatestAnalysisRun(jobId: string): Promise<AnalysisRun> {
  return requireData(await apiClient.GET("/api/v1/jobs/{job_id}/analysis-runs/latest", {
    cache: "no-store",
    params: { path: { job_id: jobId } },
  }));
}

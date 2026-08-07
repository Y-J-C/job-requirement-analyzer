import type { JobPosting } from "@/features/job-postings/types";

import type {
  AnalysisRun,
  RequirementInput,
  RequirementItem,
  RequirementListResponse,
} from "./types";


const apiBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";


async function parseResponse<T>(response: Response): Promise<T> {
  if (!response.ok) throw new Error(`Request failed with status ${response.status}`);
  return response.json() as Promise<T>;
}


export async function fetchRequirements(jobId: string): Promise<RequirementListResponse> {
  const response = await fetch(`${apiBaseUrl}/api/v1/jobs/${jobId}/requirements`, {
    cache: "no-store",
  });
  return parseResponse<RequirementListResponse>(response);
}


export async function createRequirement(
  jobId: string,
  input: RequirementInput,
): Promise<RequirementItem> {
  const response = await fetch(`${apiBaseUrl}/api/v1/jobs/${jobId}/requirements`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(input),
  });
  return parseResponse<RequirementItem>(response);
}


export async function updateRequirement(
  requirementId: string,
  input: RequirementInput,
): Promise<RequirementItem> {
  const response = await fetch(`${apiBaseUrl}/api/v1/requirements/${requirementId}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(input),
  });
  return parseResponse<RequirementItem>(response);
}


export async function deleteRequirement(requirementId: string): Promise<void> {
  const response = await fetch(`${apiBaseUrl}/api/v1/requirements/${requirementId}`, {
    method: "DELETE",
  });
  if (!response.ok) throw new Error(`Request failed with status ${response.status}`);
}


export async function confirmRequirements(jobId: string): Promise<JobPosting> {
  const response = await fetch(`${apiBaseUrl}/api/v1/jobs/${jobId}/confirm-requirements`, {
    method: "POST",
  });
  return parseResponse<JobPosting>(response);
}


export async function startAnalysis(jobId: string): Promise<AnalysisRun> {
  const response = await fetch(`${apiBaseUrl}/api/v1/jobs/${jobId}/analyze`, {
    method: "POST",
  });
  return parseResponse<AnalysisRun>(response);
}


export async function fetchAnalysisRun(runId: string): Promise<AnalysisRun> {
  const response = await fetch(`${apiBaseUrl}/api/v1/analysis-runs/${runId}`, {
    cache: "no-store",
  });
  return parseResponse<AnalysisRun>(response);
}

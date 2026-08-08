import type {
  CreateJobPostingInput,
  JobPosting,
  JobPostingListResponse,
  SourceFile,
  UploadJobPostingInput,
  UploadJobPostingResponse,
} from "./types";


const apiBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";


export class ApiRequestError extends Error {
  constructor(message: string, readonly code: string | null = null) {
    super(message);
  }
}


async function parseResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    let code: string | null = null;
    try {
      const payload = await response.json() as { detail?: { code?: string } };
      code = payload.detail?.code ?? null;
    } catch {
      // Keep the public error generic when the API response is not JSON.
    }
    throw new ApiRequestError(`Request failed with status ${response.status}`, code);
  }
  return response.json() as Promise<T>;
}


export async function fetchJobPostings(roleId: string): Promise<JobPostingListResponse> {
  const response = await fetch(`${apiBaseUrl}/api/v1/target-roles/${roleId}/jobs`, {
    cache: "no-store",
  });
  return parseResponse<JobPostingListResponse>(response);
}


export async function fetchJobPosting(jobId: string): Promise<JobPosting> {
  const response = await fetch(`${apiBaseUrl}/api/v1/jobs/${jobId}`, {
    cache: "no-store",
  });
  return parseResponse<JobPosting>(response);
}


export async function createJobPosting(
  roleId: string,
  input: CreateJobPostingInput,
): Promise<JobPosting> {
  const response = await fetch(`${apiBaseUrl}/api/v1/target-roles/${roleId}/jobs`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(input),
  });
  return parseResponse<JobPosting>(response);
}


export async function uploadJobPosting(
  roleId: string,
  input: UploadJobPostingInput,
): Promise<UploadJobPostingResponse> {
  const body = new FormData();
  body.set("company_name", input.company_name);
  body.set("job_title", input.job_title);
  body.set("recruitment_stage", input.recruitment_stage);
  if (input.city) body.set("city", input.city);
  if (input.source_url) body.set("source_url", input.source_url);
  body.set("file", input.file);
  const response = await fetch(`${apiBaseUrl}/api/v1/target-roles/${roleId}/jobs/upload`, {
    method: "POST",
    body,
  });
  return parseResponse<UploadJobPostingResponse>(response);
}


export async function fetchSourceFile(jobId: string): Promise<SourceFile> {
  const response = await fetch(`${apiBaseUrl}/api/v1/jobs/${jobId}/source-file`, {
    cache: "no-store",
  });
  return parseResponse<SourceFile>(response);
}


export async function deleteJobPosting(jobId: string): Promise<void> {
  const response = await fetch(`${apiBaseUrl}/api/v1/jobs/${jobId}`, {
    method: "DELETE",
  });
  if (!response.ok) {
    throw new Error(`Request failed with status ${response.status}`);
  }
}

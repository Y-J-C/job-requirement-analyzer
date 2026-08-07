import type {
  CreateJobPostingInput,
  JobPosting,
  JobPostingListResponse,
} from "./types";


const apiBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";


async function parseResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    throw new Error(`Request failed with status ${response.status}`);
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


export async function deleteJobPosting(jobId: string): Promise<void> {
  const response = await fetch(`${apiBaseUrl}/api/v1/jobs/${jobId}`, {
    method: "DELETE",
  });
  if (!response.ok) {
    throw new Error(`Request failed with status ${response.status}`);
  }
}

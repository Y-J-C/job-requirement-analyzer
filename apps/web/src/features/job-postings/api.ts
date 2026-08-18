import {
  ApiRequestError,
  apiClient,
  requireData,
  requireSuccess,
} from "@/lib/api-client";

import type {
  CreateJobPostingInput,
  JobIntakeInput,
  JobIntakeResponse,
  JobMetadataUpdate,
  JobPosting,
  JobPostingListResponse,
  SourceFile,
  UploadJobPostingInput,
  UploadJobPostingResponse,
} from "./types";


export { ApiRequestError };


function appendOptional(body: FormData, name: string, value: string | null | undefined) {
  if (value) body.set(name, value);
}


export async function fetchJobPostings(roleId: string): Promise<JobPostingListResponse> {
  return requireData(await apiClient.GET("/api/v1/target-roles/{role_id}/jobs", {
    cache: "no-store",
    params: { path: { role_id: roleId } },
  }));
}


export async function fetchAllJobPostings(roleId: string): Promise<JobPostingListResponse> {
  const items: JobPosting[] = [];
  const limit = 100;
  let total = 0;
  do {
    const page = requireData(await apiClient.GET("/api/v1/target-roles/{role_id}/jobs", {
      cache: "no-store",
      params: {
        path: { role_id: roleId },
        query: { offset: items.length, limit },
      },
    }));
    items.push(...page.items);
    total = page.total;
    if (page.items.length === 0) break;
  } while (items.length < total);
  return { items, total };
}


export async function fetchJobPosting(jobId: string): Promise<JobPosting> {
  return requireData(await apiClient.GET("/api/v1/jobs/{job_id}", {
    cache: "no-store",
    params: { path: { job_id: jobId } },
  }));
}


export async function createJobPosting(
  roleId: string,
  input: CreateJobPostingInput,
): Promise<JobPosting> {
  return requireData(await apiClient.POST("/api/v1/target-roles/{role_id}/jobs", {
    params: { path: { role_id: roleId } },
    body: input,
  }));
}


export async function uploadJobPosting(
  roleId: string,
  input: UploadJobPostingInput,
): Promise<UploadJobPostingResponse> {
  const form = new FormData();
  form.set("company_name", input.company_name);
  form.set("job_title", input.job_title);
  form.set("recruitment_stage", input.recruitment_stage);
  appendOptional(form, "city", input.city);
  appendOptional(form, "source_url", input.source_url);
  form.set("file", input.file);
  return requireData(await apiClient.POST("/api/v1/target-roles/{role_id}/jobs/upload", {
    params: { path: { role_id: roleId } },
    body: { ...input, file: input.file.name },
    bodySerializer: () => form,
  }));
}


export async function intakeJobPosting(
  roleId: string,
  input: JobIntakeInput,
): Promise<JobIntakeResponse> {
  const form = new FormData();
  form.set("source_type", input.source_type);
  form.set("recruitment_stage", input.recruitment_stage);
  appendOptional(form, "company_name", input.company_name);
  appendOptional(form, "job_title", input.job_title);
  appendOptional(form, "city", input.city);
  appendOptional(form, "source_url", input.source_url);
  appendOptional(form, "text", input.text);
  input.files.forEach((file) => form.append("files", file));
  return requireData(await apiClient.POST("/api/v1/target-roles/{role_id}/jobs/intake", {
    params: { path: { role_id: roleId } },
    body: { ...input, files: input.files.map((file) => file.name) },
    bodySerializer: () => form,
  }));
}


export async function updateJobMetadata(
  jobId: string,
  input: JobMetadataUpdate,
): Promise<JobPosting> {
  return requireData(await apiClient.PATCH("/api/v1/jobs/{job_id}", {
    params: { path: { job_id: jobId } },
    body: input,
  }));
}


export async function retryJob(jobId: string): Promise<JobIntakeResponse> {
  return requireData(await apiClient.POST("/api/v1/jobs/{job_id}/retry", {
    params: { path: { job_id: jobId } },
  }));
}


export async function fetchSourceFile(jobId: string): Promise<SourceFile> {
  return requireData(await apiClient.GET("/api/v1/jobs/{job_id}/source-file", {
    cache: "no-store",
    params: { path: { job_id: jobId } },
  }));
}


export async function deleteJobPosting(jobId: string): Promise<void> {
  const result = await apiClient.DELETE("/api/v1/jobs/{job_id}", {
    params: { path: { job_id: jobId } },
  });
  requireSuccess(result);
}

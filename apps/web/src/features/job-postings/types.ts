import type { RecruitmentStage } from "@/features/target-roles/types";


export type JobPostingStatus =
  | "draft"
  | "queued"
  | "extracting"
  | "analyzing"
  | "review_required"
  | "confirmed"
  | "failed";

export type JobPosting = {
  id: string;
  active_analysis_run_id: string | null;
  target_role_id: string;
  company_name: string;
  job_title: string;
  recruitment_stage: RecruitmentStage;
  city: string | null;
  source_url: string | null;
  original_text: string;
  status: JobPostingStatus;
  collected_at: string;
  created_at: string;
  updated_at: string;
};

export type JobPostingListResponse = {
  items: JobPosting[];
  total: number;
};

export type CreateJobPostingInput = {
  company_name: string;
  job_title: string;
  recruitment_stage: RecruitmentStage;
  city: string | null;
  source_url: string | null;
  original_text: string;
};

export type UploadJobPostingInput = Omit<CreateJobPostingInput, "original_text"> & {
  file: File;
};

export type SourceFileStatus = "pending" | "running" | "succeeded" | "failed";

export type SourceFile = {
  id: string;
  job_posting_id: string;
  original_filename: string;
  declared_mime_type: string;
  detected_media_type: string;
  size_bytes: number;
  sha256: string;
  parse_status: SourceFileStatus;
  parser_version: string | null;
  error_code: string | null;
  created_at: string;
  updated_at: string;
};

export type UploadJobPostingResponse = {
  job: JobPosting;
  source_file: SourceFile;
};

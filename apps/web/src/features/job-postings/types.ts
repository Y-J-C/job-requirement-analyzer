import type { components } from "@/generated/api-schema";
import type { RecruitmentStage } from "@/features/target-roles/types";


export type JobPostingStatus = components["schemas"]["JobPostingStatus"];
export type JobPosting = components["schemas"]["JobPostingResponse"];
export type JobPostingListResponse = components["schemas"]["JobPostingListResponse"];
export type CreateJobPostingInput = components["schemas"]["JobPostingCreate"];
export type SourceFileStatus = components["schemas"]["SourceFileStatus"];
export type SourceFile = components["schemas"]["SourceFileResponse"];
export type UploadJobPostingResponse = components["schemas"]["JobPostingUploadResponse"];
export type JobSourceType = components["schemas"]["JobSourceType"];
export type JobIntakeResponse = components["schemas"]["JobIntakeResponse"];
export type JobMetadataUpdate = components["schemas"]["JobPostingMetadataUpdate"];

export type UploadJobPostingInput = Omit<CreateJobPostingInput, "original_text"> & {
  file: File;
};

export type JobIntakeInput = {
  source_type: JobSourceType;
  company_name: string | null;
  job_title: string | null;
  recruitment_stage: RecruitmentStage;
  city: string | null;
  source_url: string | null;
  text: string | null;
  files: File[];
};

export type AnalysisRunSummary = Pick<
  components["schemas"]["AnalysisRunResponse"],
  "id" | "version" | "status"
>;

import type {
  RequirementExplicitness,
  RequirementType,
} from "@/features/requirements/types";


export type SummaryEvidence = {
  requirement_id: string;
  job_id: string;
  company_name: string;
  job_title: string;
  original_text: string;
  explicitness: RequirementExplicitness;
};

export type RequirementSummaryItem = {
  normalized_name: string;
  requirement_type: RequirementType;
  mentioning_job_count: number;
  confirmed_job_count: number;
  coverage_rate: number;
  evidence_count: number;
  explicit_evidence_count: number;
  evidence: SummaryEvidence[];
};

export type TargetRoleSummary = {
  target_role_id: string;
  target_role_name: string;
  sample_job_count: number;
  confirmed_job_count: number;
  sample_size_notice: string;
  items: RequirementSummaryItem[];
};

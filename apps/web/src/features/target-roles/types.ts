export const recruitmentStageLabels = {
  daily_internship: "日常实习",
  summer_internship: "暑期实习",
  winter_internship: "寒假实习",
  autumn_recruitment: "秋招",
  spring_recruitment: "春招",
  other: "其他",
} as const;

export type RecruitmentStage = keyof typeof recruitmentStageLabels;

export type TargetRole = {
  id: string;
  name: string;
  recruitment_stage: RecruitmentStage;
  description: string | null;
  created_at: string;
  updated_at: string;
  job_count: number;
};

export type TargetRoleListResponse = {
  items: TargetRole[];
  total: number;
};

export type CreateTargetRoleInput = {
  name: string;
  recruitment_stage: RecruitmentStage;
  description: string | null;
};

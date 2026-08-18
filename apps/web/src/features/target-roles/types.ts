import type { components } from "@/generated/api-schema";


export const recruitmentStageLabels = {
  daily_internship: "日常实习",
  summer_internship: "暑期实习",
  winter_internship: "寒假实习",
  autumn_recruitment: "秋招",
  spring_recruitment: "春招",
  other: "其他",
} as const;

export type RecruitmentStage = components["schemas"]["RecruitmentStage"];
export type TargetRole = components["schemas"]["TargetRoleResponse"];
export type TargetRoleListResponse = components["schemas"]["TargetRoleListResponse"];
export type CreateTargetRoleInput = components["schemas"]["TargetRoleCreate"];

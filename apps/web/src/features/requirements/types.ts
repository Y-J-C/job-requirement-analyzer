import type { components } from "@/generated/api-schema";


export type RequirementType = components["schemas"]["RequirementType"];
export type RequirementExplicitness = components["schemas"]["RequirementExplicitness"];
export type RequirementItem = components["schemas"]["RequirementItemResponse"];
export type RequirementInput = components["schemas"]["RequirementItemCreate"];
export type RequirementListResponse = components["schemas"]["RequirementItemListResponse"];
export type AnalysisRunStatus = components["schemas"]["AnalysisRunStatus"];
export type AnalysisRun = components["schemas"]["AnalysisRunResponse"];

export const requirementTypeLabels: Record<RequirementType, string> = {
  eligibility: "资格门槛",
  core_competency: "核心能力",
  experience: "经历门槛",
  preferred: "加分条件",
  uncertain: "待确认",
};

export const explicitnessLabels: Record<RequirementExplicitness, string> = {
  explicit: "原文明示",
  implicit: "句式隐含",
  uncertain: "无法确定",
};

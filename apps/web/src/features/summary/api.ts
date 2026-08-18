import type { RequirementType } from "@/features/requirements/types";
import { apiClient, requireData } from "@/lib/api-client";

import type { TargetRoleSummary } from "./types";


export async function fetchTargetRoleSummary(
  roleId: string,
  requirementType: RequirementType | "all",
): Promise<TargetRoleSummary> {
  return requireData(await apiClient.GET("/api/v1/target-roles/{role_id}/summary", {
    cache: "no-store",
    params: {
      path: { role_id: roleId },
      query: { requirement_type: requirementType === "all" ? null : requirementType },
    },
  }));
}


export async function createSelectedSummary(
  roleId: string,
  jobIds: string[],
): Promise<TargetRoleSummary> {
  return requireData(await apiClient.POST("/api/v1/target-roles/{role_id}/summary", {
    params: { path: { role_id: roleId } },
    body: { job_ids: jobIds },
  }));
}

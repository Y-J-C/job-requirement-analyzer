import type { RequirementType } from "@/features/requirements/types";

import type { TargetRoleSummary } from "./types";


const apiBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";


export async function fetchTargetRoleSummary(
  roleId: string,
  requirementType: RequirementType | "all",
): Promise<TargetRoleSummary> {
  const query = requirementType === "all"
    ? ""
    : `?${new URLSearchParams({ requirement_type: requirementType })}`;
  const response = await fetch(`${apiBaseUrl}/api/v1/target-roles/${roleId}/summary${query}`, {
    cache: "no-store",
  });
  if (!response.ok) throw new Error(`Request failed with status ${response.status}`);
  return response.json() as Promise<TargetRoleSummary>;
}

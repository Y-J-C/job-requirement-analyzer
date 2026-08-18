import { apiClient, requireData } from "@/lib/api-client";

import type {
  CreateTargetRoleInput,
  TargetRole,
  TargetRoleListResponse,
} from "./types";


export async function fetchTargetRoles(): Promise<TargetRoleListResponse> {
  return requireData(await apiClient.GET("/api/v1/target-roles", { cache: "no-store" }));
}


export async function fetchTargetRole(roleId: string): Promise<TargetRole> {
  return requireData(await apiClient.GET("/api/v1/target-roles/{role_id}", {
    cache: "no-store",
    params: { path: { role_id: roleId } },
  }));
}


export async function createTargetRole(input: CreateTargetRoleInput): Promise<TargetRole> {
  return requireData(await apiClient.POST("/api/v1/target-roles", { body: input }));
}

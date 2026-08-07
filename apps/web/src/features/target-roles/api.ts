import type {
  CreateTargetRoleInput,
  TargetRole,
  TargetRoleListResponse,
} from "./types";


const apiBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";


async function parseResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    throw new Error(`Request failed with status ${response.status}`);
  }
  return response.json() as Promise<T>;
}


export async function fetchTargetRoles(): Promise<TargetRoleListResponse> {
  const response = await fetch(`${apiBaseUrl}/api/v1/target-roles`, {
    cache: "no-store",
  });
  return parseResponse<TargetRoleListResponse>(response);
}


export async function fetchTargetRole(roleId: string): Promise<TargetRole> {
  const response = await fetch(`${apiBaseUrl}/api/v1/target-roles/${roleId}`, {
    cache: "no-store",
  });
  return parseResponse<TargetRole>(response);
}


export async function createTargetRole(input: CreateTargetRoleInput): Promise<TargetRole> {
  const response = await fetch(`${apiBaseUrl}/api/v1/target-roles`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(input),
  });
  return parseResponse<TargetRole>(response);
}

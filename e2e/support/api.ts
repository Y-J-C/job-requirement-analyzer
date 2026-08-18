import type { APIRequestContext, APIResponse } from "@playwright/test";

export const apiBaseUrl = process.env.E2E_API_BASE_URL ?? "http://localhost:18000";

type TargetRole = {
  id: string;
  name: string;
};

type TargetRoleList = {
  items: TargetRole[];
  total: number;
};

function runMarker(): string {
  const runId = process.env.E2E_RUN_ID;
  if (!runId) throw new Error("E2E_RUN_ID is not configured");
  return `[E2E:${runId}]`;
}

export function taggedName(name: string): string {
  return `${runMarker()} ${name}`;
}

export async function createTargetRole(
  request: APIRequestContext,
  name: string,
): Promise<TargetRole> {
  const response = await request.post(`${apiBaseUrl}/api/v1/target-roles`, {
    data: {
      name,
      recruitment_stage: "daily_internship",
      description: "Playwright 自动化测试数据",
    },
  });
  if (!response.ok()) {
    throw new Error(`创建测试目标方向失败（HTTP ${response.status()}）`);
  }
  return response.json();
}

export function getTargetRole(
  request: APIRequestContext,
  roleId: string,
): Promise<APIResponse> {
  return request.get(`${apiBaseUrl}/api/v1/target-roles/${roleId}`);
}

export async function deleteTargetRole(
  request: APIRequestContext,
  roleId: string,
): Promise<void> {
  const response = await request.delete(`${apiBaseUrl}/api/v1/target-roles/${roleId}`);
  if (![204, 404].includes(response.status())) {
    throw new Error(`清理测试目标方向失败（HTTP ${response.status()}）`);
  }
}

export async function cleanupRunResources(request: APIRequestContext): Promise<void> {
  const roles: TargetRole[] = [];
  let offset = 0;

  while (true) {
    const response = await request.get(`${apiBaseUrl}/api/v1/target-roles`, {
      params: { offset, limit: 100 },
    });
    if (!response.ok()) {
      throw new Error(`读取测试清理列表失败（HTTP ${response.status()}）`);
    }
    const page = (await response.json()) as TargetRoleList;
    roles.push(...page.items);
    offset += page.items.length;
    if (offset >= page.total || page.items.length === 0) break;
  }

  const marker = runMarker();
  for (const role of roles.filter((item) => item.name.startsWith(marker))) {
    await deleteTargetRole(request, role.id);
  }
}

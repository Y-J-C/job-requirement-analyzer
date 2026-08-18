import createClient from "openapi-fetch";

import type { components, paths } from "@/generated/api-schema";


const apiBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export function applicationFetch(request: Request): Promise<Response> {
  return globalThis.fetch(request);
}


export const apiClient = createClient<paths>({
  baseUrl: apiBaseUrl,
  fetch: applicationFetch,
});

export type ProblemDetails = components["schemas"]["ProblemDetails"];

type ApiResult<T> = {
  data?: T;
  error?: unknown;
  response: Response;
};


export class ApiRequestError extends Error {
  constructor(
    message: string,
    readonly status: number,
    readonly code: string | null = null,
    readonly problem: ProblemDetails | null = null,
  ) {
    super(message);
    this.name = "ApiRequestError";
  }
}


function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}


function toApiRequestError(response: Response, error: unknown): ApiRequestError {
  if (isRecord(error)) {
    const legacyDetail = isRecord(error.detail) ? error.detail : null;
    const detail = typeof error.detail === "string"
      ? error.detail
      : typeof legacyDetail?.message === "string"
        ? legacyDetail.message
        : `Request failed with status ${response.status}`;
    const code = typeof error.code === "string"
      ? error.code
      : typeof legacyDetail?.code === "string"
        ? legacyDetail.code
        : null;
    const problem = typeof error.title === "string" && typeof error.status === "number"
      ? error as ProblemDetails
      : null;
    return new ApiRequestError(detail, response.status, code, problem);
  }
  return new ApiRequestError(`Request failed with status ${response.status}`, response.status);
}


export function requireData<T>(result: ApiResult<T>): T {
  if (!result.response.ok) throw toApiRequestError(result.response, result.error);
  if (result.data === undefined) {
    throw new ApiRequestError("API returned no response data", result.response.status);
  }
  return result.data;
}


export function requireSuccess(result: Omit<ApiResult<never>, "data">): void {
  if (!result.response.ok) throw toApiRequestError(result.response, result.error);
}

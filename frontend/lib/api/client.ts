import { API_BASE_URL, API_V1_PREFIX } from "@/lib/constants";
import { ApiErrorResponse, HealthStatusResponse } from "@/types/api";
import { EnergyScenario, OptimizationResponse } from "@/types/energy";

async function request<T>(
  path: string,
  init?: RequestInit
): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    headers: { "Content-Type": "application/json", ...init?.headers },
    cache: "no-store",
    ...init,
  });

  if (!response.ok) {
    let detail = `Request to ${path} failed with status ${response.status}.`;
    try {
      const body = (await response.json()) as ApiErrorResponse;
      if (body?.detail) {
        detail = typeof body.detail === "string" ? body.detail : JSON.stringify(body.detail);
      }
    } catch {
      // Response body was not JSON; keep the status-based message.
    }
    throw new Error(detail);
  }

  return (await response.json()) as T;
}

/** Strongly typed client for the Smart Campus Energy Optimization API. */
export const apiClient = {
  /** GET /api/v1/health */
  checkHealth(): Promise<HealthStatusResponse> {
    return request<HealthStatusResponse>(`${API_V1_PREFIX}/health`);
  },

  /** POST /api/v1/optimize-energy */
  optimizeEnergy(scenario: EnergyScenario): Promise<OptimizationResponse> {
    return request<OptimizationResponse>(`${API_V1_PREFIX}/optimize-energy`, {
      method: "POST",
      body: JSON.stringify(scenario),
    });
  },
};

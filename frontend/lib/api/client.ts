import { HealthStatusResponse } from "@/types/api";
import { EnergyScenario, OptimizationResponse } from "@/types/energy";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export const apiClient = {
  async checkHealth(): Promise<HealthStatusResponse> {
    try {
      const res = await fetch(`${API_BASE}/health`, {
        cache: "no-store",
      });
      if (!res.ok) {
        return { status: "error" };
      }
      return await res.json();
    } catch {
      return { status: "error" };
    }
  },

  async optimizeEnergy(scenario: EnergyScenario): Promise<OptimizationResponse> {
    const res = await fetch(`${API_BASE}/api/v1/optimize-energy`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(scenario),
    });

    if (!res.ok) {
      let errorMsg = `Optimization failed with status ${res.status}`;
      try {
        const errorData = await res.json();
        if (errorData.detail) {
          errorMsg =
            typeof errorData.detail === "string"
              ? errorData.detail
              : JSON.stringify(errorData.detail);
        }
      } catch {
        // use default error message
      }
      throw new Error(errorMsg);
    }

    return await res.json();
  },
};

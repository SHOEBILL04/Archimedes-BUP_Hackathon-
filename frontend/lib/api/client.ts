import { HealthStatusResponse } from "@/types/api";
import { EnergyScenario, OptimizationResponse } from "@/types/energy";

function resolveApiBase(): string {
  const rawUrl = process.env.NEXT_PUBLIC_API_URL;
  if (rawUrl && rawUrl.trim()) {
    const trimmed = rawUrl.trim().replace(/\/+$/, "");
    if (trimmed.startsWith("http://") || trimmed.startsWith("https://")) {
      return trimmed;
    }
    return `https://${trimmed}`;
  }

  // If in browser on any deployed domain (such as *.vercel.app)
  if (typeof window !== "undefined") {
    const host = window.location.hostname;
    if (host && host !== "localhost" && host !== "127.0.0.1" && host !== "0.0.0.0") {
      return "https://archimedes-energy-backend.onrender.com";
    }
  }

  if (process.env.NODE_ENV === "production") {
    return "https://archimedes-energy-backend.onrender.com";
  }

  return "http://localhost:8000";
}

export const apiClient = {
  async checkHealth(): Promise<HealthStatusResponse> {
    const apiBase = resolveApiBase();
    try {
      const res = await fetch(`${apiBase}/health`, {
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
    const apiBase = resolveApiBase();
    const res = await fetch(`${apiBase}/api/v1/optimize-energy`, {
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

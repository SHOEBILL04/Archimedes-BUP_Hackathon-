import { HealthStatusResponse } from "@/types/api";
import { EnergyScenario, OptimizationResponse } from "@/types/energy";

function resolveApiBase(): string {
  // If in browser on any deployed domain (such as *.vercel.app)
  if (typeof window !== "undefined") {
    const host = window.location.hostname;
    if (host && host !== "localhost" && host !== "127.0.0.1" && host !== "0.0.0.0") {
      // Route through same-origin proxy to completely bypass browser adblockers (ERR_BLOCKED_BY_CLIENT)
      return "/api/py";
    }
  }

  const rawUrl = process.env.NEXT_PUBLIC_API_URL;
  if (rawUrl && rawUrl.trim()) {
    const trimmed = rawUrl.trim().replace(/\/+$/, "");
    if (trimmed.startsWith("http://") || trimmed.startsWith("https://")) {
      return trimmed;
    }
    return `https://${trimmed}`;
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
      if (res.ok) {
        return await res.json();
      }
    } catch {
      // If same-origin proxy failed, attempt direct fallback
    }

    // Direct fallback attempt if proxy had an issue
    if (apiBase.startsWith("/")) {
      try {
        const directRes = await fetch("https://archimedes-energy-backend.onrender.com/health", {
          cache: "no-store",
        });
        if (directRes.ok) {
          return await directRes.json();
        }
      } catch {
        // blocked by client or offline
      }
    }

    return { status: "error" };
  },

  async optimizeEnergy(scenario: EnergyScenario): Promise<OptimizationResponse> {
    const apiBase = resolveApiBase();
    let res: Response | null = null;

    try {
      res = await fetch(`${apiBase}/api/v1/optimize-energy`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(scenario),
      });
    } catch {
      // Network error calling proxy
    }

    // If proxy failed, timed out, or returned 502, automatically fall back to direct backend
    if ((!res || !res.ok) && apiBase.startsWith("/")) {
      try {
        const directRes = await fetch("https://archimedes-energy-backend.onrender.com/api/v1/optimize-energy", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify(scenario),
        });
        if (directRes.ok) {
          return await directRes.json();
        }
        res = directRes;
      } catch {
        // Direct call failed or blocked
      }
    }

    if (!res || !res.ok) {
      let errorMsg = res ? `Optimization failed with status ${res.status}` : "Optimization service connection failed";
      try {
        if (res) {
          const errorData = await res.json();
          if (errorData.detail) {
            errorMsg =
              typeof errorData.detail === "string"
                ? errorData.detail
                : JSON.stringify(errorData.detail);
          }
        }
      } catch {
        // use default error message
      }
      throw new Error(errorMsg);
    }

    return await res.json();
  },
};

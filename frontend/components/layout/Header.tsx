"use client";

import React, { useEffect, useState } from "react";
import { Badge } from "@/components/ui/badge";
import { apiClient } from "@/lib/api/client";
import { CheckCircle2, AlertCircle, RefreshCw, Terminal } from "lucide-react";

export function Header({
  title = "Smart Campus Energy Optimization",
}: {
  title?: string;
}) {
  const [healthStatus, setHealthStatus] = useState<"checking" | "ok" | "error">(
    "checking"
  );

  const verifyHealth = React.useCallback(() => {
    setHealthStatus("checking");
    apiClient
      .checkHealth()
      .then((res) => {
        setHealthStatus(res.status === "ok" ? "ok" : "error");
      })
      .catch(() => {
        setHealthStatus("error");
      });
  }, []);

  useEffect(() => {
    verifyHealth();

    // Periodically poll every 10 seconds to detect when backend is awake
    const interval = setInterval(() => {
      apiClient.checkHealth().then((res) => {
        if (res.status === "ok") {
          setHealthStatus("ok");
        }
      }).catch(() => {});
    }, 10000);

    return () => clearInterval(interval);
  }, [verifyHealth]);

  return (
    <header className="h-16 border-b border-slate-200/90 bg-white/90 backdrop-blur-md px-8 flex items-center justify-between sticky top-0 z-20">
      <div className="flex items-center gap-3">
        <h2 className="text-sm font-bold text-[#0F172A] tracking-tight">{title}</h2>
        <Badge variant="emerald" className="font-mono text-[10px] hidden sm:inline-flex">
          BUP CSE Fest 2026
        </Badge>
      </div>

      <div className="flex items-center gap-4">
        {/* API Health indicator */}
        <div className="flex items-center gap-2">
          {healthStatus === "ok" ? (
            <Badge variant="emerald" className="flex items-center gap-1.5 py-1 px-3 select-none">
              <span className="flex h-1.5 w-1.5 rounded-full bg-emerald-500 animate-pulse" />
              <CheckCircle2 className="h-3.5 w-3.5 text-emerald-600" />
              <span className="font-mono text-[11px] text-emerald-800">API 200 OK</span>
            </Badge>
          ) : healthStatus === "checking" ? (
            <Badge variant="secondary" className="flex items-center gap-1.5 py-1 px-3 font-mono text-[11px]">
              <RefreshCw className="h-3.5 w-3.5 animate-spin text-slate-500" />
              <span>Connecting...</span>
            </Badge>
          ) : (
            <button
              type="button"
              onClick={verifyHealth}
              title="Click to re-check API connection"
              className="focus:outline-none"
            >
              <Badge variant="coral" className="flex items-center gap-1.5 py-1 px-3 font-mono text-[11px] cursor-pointer hover:opacity-85 transition-opacity">
                <AlertCircle className="h-3.5 w-3.5" />
                <span>API Offline (Retry)</span>
              </Badge>
            </button>
          )}
        </div>

        <div className="h-4 w-[1px] bg-slate-200 hidden sm:block" />

        <div className="hidden sm:flex items-center gap-1.5 text-xs text-slate-500 font-mono">
          <Terminal className="h-3.5 w-3.5 text-slate-700" />
          <span>CBC Solver</span>
        </div>
      </div>
    </header>
  );
}

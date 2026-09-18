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

  useEffect(() => {
    let isMounted = true;
    apiClient
      .checkHealth()
      .then((res) => {
        if (isMounted) {
          setHealthStatus(res.status === "ok" ? "ok" : "error");
        }
      })
      .catch(() => {
        if (isMounted) {
          setHealthStatus("error");
        }
      });

    return () => {
      isMounted = false;
    };
  }, []);

  return (
    <header className="h-16 border-b border-slate-200/90 bg-white/90 backdrop-blur-md px-8 flex items-center justify-between sticky top-0 z-20">
      <div className="flex items-center gap-3">
        <h2 className="text-sm font-bold text-[#425B9A] tracking-tight">{title}</h2>
        <Badge variant="cream" className="font-mono text-[10px] hidden sm:inline-flex">
          BUP CSE Fest 2026
        </Badge>
      </div>

      <div className="flex items-center gap-4">
        {/* API Health indicator */}
        <div className="flex items-center gap-2">
          {healthStatus === "ok" ? (
            <Badge variant="sky" className="flex items-center gap-1.5 py-1 px-3">
              <span className="flex h-1.5 w-1.5 rounded-full bg-[#425B9A] animate-pulse" />
              <CheckCircle2 className="h-3.5 w-3.5 text-[#425B9A]" />
              <span className="font-mono text-[11px] text-[#425B9A]">API 200 OK</span>
            </Badge>
          ) : healthStatus === "checking" ? (
            <Badge variant="secondary" className="flex items-center gap-1.5 py-1 px-3 font-mono text-[11px]">
              <RefreshCw className="h-3.5 w-3.5 animate-spin text-slate-500" />
              <span>Connecting...</span>
            </Badge>
          ) : (
            <Badge variant="coral" className="flex items-center gap-1.5 py-1 px-3 font-mono text-[11px]">
              <AlertCircle className="h-3.5 w-3.5" />
              <span>API Offline (:8000)</span>
            </Badge>
          )}
        </div>

        <div className="h-4 w-[1px] bg-slate-200 hidden sm:block" />

        <div className="hidden sm:flex items-center gap-1.5 text-xs text-slate-500 font-mono">
          <Terminal className="h-3.5 w-3.5 text-[#425B9A]" />
          <span>CBC Solver</span>
        </div>
      </div>
    </header>
  );
}

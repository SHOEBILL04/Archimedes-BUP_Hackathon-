"use client";

import React, { useEffect, useState } from "react";
import { Badge } from "@/components/ui/badge";
import { apiClient } from "@/lib/api/client";
import { CheckCircle2, AlertCircle, RefreshCw, Terminal } from "lucide-react";

type HealthState = "checking" | "ok" | "error";

export function Header({
  title = "Smart Campus Energy Optimization",
}: {
  title?: string;
}) {
  const [healthStatus, setHealthStatus] = useState<HealthState>("checking");

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
    <header className="sticky top-0 z-20 flex h-16 items-center justify-between border-b border-line bg-surface/90 px-8 backdrop-blur-md">
      <div className="flex items-center gap-3">
        <h2 className="text-sm font-bold tracking-tight text-brand">{title}</h2>
        <Badge variant="cream" className="hidden font-mono text-[10px] sm:inline-flex">
          BUP CSE Fest 2026
        </Badge>
      </div>

      <div className="flex items-center gap-4">
        <div
          className="flex items-center gap-2"
          role="status"
          aria-live="polite"
        >
          {healthStatus === "ok" ? (
            <Badge
              variant="accent"
              className="flex items-center gap-1.5 px-3 py-1 font-mono text-[11px]"
            >
              <span className="flex h-1.5 w-1.5 animate-pulse rounded-full bg-accent-600" />
              <CheckCircle2 className="h-3.5 w-3.5" />
              <span>API 200 OK</span>
            </Badge>
          ) : healthStatus === "checking" ? (
            <Badge
              variant="neutral"
              className="flex items-center gap-1.5 px-3 py-1 font-mono text-[11px]"
            >
              <RefreshCw className="h-3.5 w-3.5 animate-spin" />
              <span>Connecting...</span>
            </Badge>
          ) : (
            <Badge
              variant="coral"
              className="flex items-center gap-1.5 px-3 py-1 font-mono text-[11px]"
            >
              <AlertCircle className="h-3.5 w-3.5" />
              <span>API Offline (:8000)</span>
            </Badge>
          )}
        </div>

        <div className="hidden h-4 w-px bg-line sm:block" />

        <div className="hidden items-center gap-1.5 font-mono text-xs text-ink-muted sm:flex">
          <Terminal className="h-3.5 w-3.5 text-brand" />
          <span>CBC Solver</span>
        </div>
      </div>
    </header>
  );
}

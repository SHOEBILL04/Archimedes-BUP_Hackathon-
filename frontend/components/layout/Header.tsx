"use client";

import React, { useEffect, useState } from "react";
import { Badge } from "@/components/ui/badge";
import { apiClient } from "@/lib/api/client";
import { CheckCircle2, AlertCircle, RefreshCw } from "lucide-react";

export function Header({
  title = "Smart Campus Energy Optimization Platform",
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
    <header className="h-16 border-b border-slate-800/80 bg-slate-950/60 backdrop-blur-md px-8 flex items-center justify-between sticky top-0 z-10">
      <div className="flex items-center gap-3">
        <h2 className="text-base font-semibold text-slate-100">{title}</h2>
        <span className="text-xs px-2 py-0.5 rounded-full bg-slate-800 text-slate-400 border border-slate-700">
          BUP Hackathon 2026
        </span>
      </div>

      <div className="flex items-center gap-4">
        {/* API Health indicator */}
        <div className="flex items-center gap-2">
          {healthStatus === "ok" ? (
            <Badge variant="success" className="flex items-center gap-1.5 py-1">
              <CheckCircle2 className="h-3.5 w-3.5 text-teal-400" />
              <span>FastAPI Online</span>
            </Badge>
          ) : healthStatus === "checking" ? (
            <Badge variant="secondary" className="flex items-center gap-1.5 py-1">
              <RefreshCw className="h-3.5 w-3.5 animate-spin text-slate-400" />
              <span>Connecting...</span>
            </Badge>
          ) : (
            <Badge variant="warning" className="flex items-center gap-1.5 py-1">
              <AlertCircle className="h-3.5 w-3.5 text-amber-400" />
              <span>API Offline (localhost:8000)</span>
            </Badge>
          )}
        </div>
      </div>
    </header>
  );
}

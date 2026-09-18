"use client";

import React, { useState } from "react";
import { PageContainer } from "@/components/layout/PageContainer";
import { ScenarioForm } from "@/components/energy/ScenarioForm";
import { OptimizationSummary } from "@/components/energy/OptimizationSummary";
import { ScheduleTable } from "@/components/energy/ScheduleTable";
import { DirectivesCard } from "@/components/energy/DirectivesCard";
import { DemandChart } from "@/components/charts/DemandChart";
import { SolarChart } from "@/components/charts/SolarChart";
import { BatteryChart } from "@/components/charts/BatteryChart";
import { OptimizationResponse } from "@/types/energy";
import { Sliders, Cpu } from "lucide-react";
import { Badge } from "@/components/ui/badge";

import { DEFAULT_SAMPLE_SCENARIO } from "@/lib/constants";
import { apiClient } from "@/lib/api/client";

export default function DashboardPage() {
  const [optimizationResult, setOptimizationResult] =
    useState<OptimizationResponse | null>(null);

  React.useEffect(() => {
    let isMounted = true;
    apiClient
      .optimizeEnergy(DEFAULT_SAMPLE_SCENARIO)
      .then((res) => {
        if (isMounted) setOptimizationResult(res);
      })
      .catch(() => {
        // Backend offline or error, gracefully keep null
      });
    return () => {
      isMounted = false;
    };
  }, []);

  return (
    <PageContainer title="Optimizer Workbench">
      {/* Header Banner */}
      <div className="bento-card p-6 border-slate-200/90 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <h1 className="text-xl font-bold text-[#0F172A] tracking-tight flex items-center gap-2">
              <Sliders className="h-5 w-5 text-emerald-600" />
              <span>Energy Optimization Workbench</span>
            </h1>
            <Badge variant="emerald" className="font-mono text-[10px]">
              PuLP Engine
            </Badge>
          </div>
          <p className="text-xs text-slate-500">
            Interactive dispatch tuning, operator directives simulation, and constraint feasibility audit.
          </p>
        </div>

        <div className="flex items-center gap-2 text-xs font-mono font-bold text-slate-800 bg-slate-50 border border-slate-200 px-3.5 py-2 rounded-xl w-fit shadow-2xs">
          <Cpu className="h-3.5 w-3.5 text-slate-600" />
          <span>Solver: COIN-OR CBC (Linear Program)</span>
        </div>
      </div>

      {/* KPI Metrics */}
      <OptimizationSummary result={optimizationResult} />

      {/* Asymmetric Bento Workbench Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-5">
        {/* Left Column: Directives & Scenario Console */}
        <div className="lg:col-span-5 space-y-5">
          <ScenarioForm onOptimized={setOptimizationResult} />
          <DirectivesCard
            directives={optimizationResult?.directive_interpretation}
            statusMessage={optimizationResult?.status_message}
          />
        </div>

        {/* Right Column: Visual Telemetry Stack */}
        <div className="lg:col-span-7 space-y-5">
          <DemandChart schedule={optimizationResult?.schedule} />
          <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
            <SolarChart schedule={optimizationResult?.schedule} />
            <BatteryChart schedule={optimizationResult?.schedule} />
          </div>
        </div>

        {/* Full-width 24h Schedule Matrix */}
        <div className="lg:col-span-12">
          <ScheduleTable schedule={optimizationResult?.schedule} />
        </div>
      </div>
    </PageContainer>
  );
}

"use client";

import React, { useState } from "react";
import { PageContainer } from "@/components/layout/PageContainer";
import { ScenarioForm } from "@/components/energy/ScenarioForm";
import { OptimizationSummary } from "@/components/energy/OptimizationSummary";
import { ScheduleTable } from "@/components/energy/ScheduleTable";
import { DemandChart } from "@/components/charts/DemandChart";
import { SolarChart } from "@/components/charts/SolarChart";
import { BatteryChart } from "@/components/charts/BatteryChart";
import { OptimizationResponse } from "@/types/energy";
import { Sliders, Cpu } from "lucide-react";
import { Badge } from "@/components/ui/badge";

export default function DashboardPage() {
  const [optimizationResult, setOptimizationResult] =
    useState<OptimizationResponse | null>(null);

  return (
    <PageContainer title="Optimizer Workbench">
      {/* Header Banner */}
      <div className="bento-card p-6 border-white/[0.08] flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <h1 className="text-xl font-bold text-white tracking-tight flex items-center gap-2">
              <Sliders className="h-5 w-5 text-cyan-400" />
              <span>Energy Optimization Workbench</span>
            </h1>
            <Badge variant="cyan" className="font-mono text-[10px]">
              PuLP Engine
            </Badge>
          </div>
          <p className="text-xs text-slate-400">
            Interactive dispatch tuning, operator directives simulation, and constraint feasibility audit.
          </p>
        </div>

        <div className="flex items-center gap-2 text-xs font-mono text-cyan-400 bg-cyan-950/30 border border-cyan-500/20 px-3 py-1.5 rounded-xl w-fit">
          <Cpu className="h-3.5 w-3.5" />
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

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
      <div className="bento-card bento-card-static flex flex-col justify-between gap-4 p-6 sm:flex-row sm:items-center">
        <div className="space-y-1">
          <div className="flex flex-wrap items-center gap-2">
            <h1 className="flex items-center gap-2 text-xl font-bold tracking-tight text-brand">
              <Sliders className="h-5 w-5" />
              <span>Energy Optimization Workbench</span>
            </h1>
            <Badge variant="accent" className="font-mono text-[10px]">
              PuLP Engine
            </Badge>
          </div>
          <p className="text-xs text-ink-muted">
            Interactive dispatch tuning, operator directives simulation, and
            constraint feasibility audit.
          </p>
        </div>

        <div className="flex w-fit items-center gap-2 rounded-xl border border-brand/12 bg-cream px-3.5 py-2 font-mono text-xs font-bold text-brand shadow-tile">
          <Cpu className="h-3.5 w-3.5" />
          <span>Solver: COIN-OR CBC (Linear Program)</span>
        </div>
      </div>

      <OptimizationSummary result={optimizationResult} />

      <div className="grid grid-cols-1 gap-5 lg:grid-cols-12">
        <div className="space-y-5 self-start lg:col-span-5">
          <ScenarioForm onOptimized={setOptimizationResult} />
        </div>

        <div className="space-y-5 self-start lg:col-span-7">
          <DemandChart schedule={optimizationResult?.schedule} />
          <div className="grid grid-cols-1 gap-5 md:grid-cols-2">
            <SolarChart schedule={optimizationResult?.schedule} />
            <BatteryChart schedule={optimizationResult?.schedule} />
          </div>
        </div>

        <div className="lg:col-span-12">
          <ScheduleTable schedule={optimizationResult?.schedule} />
        </div>
      </div>
    </PageContainer>
  );
}

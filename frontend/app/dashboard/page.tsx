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

export default function DashboardPage() {
  const [optimizationResult, setOptimizationResult] =
    useState<OptimizationResponse | null>(null);

  return (
    <PageContainer title="Energy Optimization Workbench">
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-bold text-white tracking-tight">
            Campus Energy Dispatch Console
          </h1>
          <p className="text-sm text-slate-400 mt-1">
            Run live simulations, evaluate operator notes against battery constraints, and review verified schedules.
          </p>
        </div>

        <OptimizationSummary result={optimizationResult} />

        <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
          <div className="xl:col-span-1">
            <ScenarioForm onOptimized={setOptimizationResult} />
          </div>
          <div className="xl:col-span-2 space-y-6">
            <DemandChart schedule={optimizationResult?.schedule} />
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <SolarChart schedule={optimizationResult?.schedule} />
              <BatteryChart schedule={optimizationResult?.schedule} />
            </div>
          </div>
        </div>

        <ScheduleTable schedule={optimizationResult?.schedule} />
      </div>
    </PageContainer>
  );
}

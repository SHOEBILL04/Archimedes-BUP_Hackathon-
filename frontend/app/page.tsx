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
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Sparkles, Zap, Cpu, ShieldCheck, ArrowRight, Activity } from "lucide-react";
import Link from "next/link";
import { formatCurrencyBDT } from "@/lib/utils";
import { DEFAULT_SAMPLE_SCENARIO } from "@/lib/constants";
import { apiClient } from "@/lib/api/client";

export default function HomePage() {
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

  const totalCost =
    optimizationResult?.total_grid_cost_bdt ??
    (optimizationResult as unknown as { total_cost_bdt?: number })?.total_cost_bdt ??
    null;

  return (
    <PageContainer title="Overview & Bento Console">
      {/* 12-Column Asymmetric Bento Grid Architecture in Clean-Tech Theme */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-12 gap-5">
        
        {/* Bento Cell 1: Hero Command Console (Modern, Cool, and Classical Midnight Slate) */}
        <div className="md:col-span-2 lg:col-span-8">
          <div className="bento-hero p-7 relative overflow-hidden h-full flex flex-col justify-between group">
            <div className="space-y-3">
              <div className="flex flex-wrap items-center gap-2">
                <Badge variant="emerald" className="font-mono gap-1.5 px-3 py-1">
                  <Sparkles className="h-3 w-3 text-emerald-600" />
                  <span>Autonomous Energy Dispatch</span>
                </Badge>
                <Badge variant="cyan" className="font-mono text-[10px]">
                  GridWise LLM Engine
                </Badge>
              </div>

              <h1 className="text-2xl sm:text-3xl font-extrabold text-[#0F172A] tracking-tight leading-tight">
                Smart Campus Energy <br className="hidden sm:inline" />
                <span className="text-emerald-700">Optimization Platform</span>
              </h1>

              <p className="text-xs sm:text-sm text-slate-600 leading-relaxed max-w-2xl font-normal">
                Multi-stage dispatch system coupling natural language operator directives with
                deterministic physical guardrails and PuLP/CBC linear programming to minimize
                grid electricity tariffs while guaranteeing battery longevity.
              </p>
            </div>

            <div className="pt-6 flex flex-wrap items-center justify-between gap-4 border-t border-slate-200/70 mt-4">
              <div className="flex flex-wrap items-center gap-4 text-xs font-mono font-medium text-slate-600">
                <div className="flex items-center gap-1.5 text-emerald-600">
                  <Zap className="h-3.5 w-3.5" />
                  <span>LP Solver</span>
                </div>
                <div className="flex items-center gap-1.5 text-sky-600">
                  <ShieldCheck className="h-3.5 w-3.5" />
                  <span>Replay Validator</span>
                </div>
                <div className="flex items-center gap-1.5 text-amber-600">
                  <Cpu className="h-3.5 w-3.5" />
                  <span>LLM Guardrails</span>
                </div>
              </div>

              <Link
                href="/dashboard"
                className="inline-flex items-center gap-1.5 text-xs font-bold text-emerald-600 hover:text-emerald-700 transition-colors group/link font-mono"
              >
                <span>Full Workbench</span>
                <ArrowRight className="h-3.5 w-3.5 group-hover/link:translate-x-1 transition-transform" />
              </Link>
            </div>
          </div>
        </div>

        {/* Bento Cell 2: Primary Cost KPI Spotlight Card */}
        <div className="md:col-span-2 lg:col-span-4">
          <Card className="bento-card p-6 h-full flex flex-col justify-between group">
            <div className="flex items-center justify-between">
              <span className="text-[11px] font-mono font-bold text-slate-500 uppercase tracking-wider">
                Objective Function Value
              </span>
              <span className="h-2.5 w-2.5 rounded-full bg-emerald-500 ring-4 ring-emerald-500/20" />
            </div>

            <div className="my-auto py-3">
              <span className="text-[11px] font-mono font-semibold text-slate-500 block mb-1">Total Grid Tariff</span>
              <h3 className="text-3xl sm:text-4xl font-extrabold font-mono text-[#0F172A] tracking-tight">
                {totalCost !== null ? formatCurrencyBDT(totalCost) : "—"}
              </h3>
              <p className="text-[11px] text-slate-500 mt-2 font-mono">
                {totalCost !== null
                  ? "Evaluated across 24 hourly time-of-use bins"
                  : "Click Run Optimization to evaluate"}
              </p>
            </div>

            <div className="pt-3 border-t border-slate-100 flex items-center justify-between text-[11px] font-mono">
              <span className="text-slate-500">Physical Balance:</span>
              <span
                className={`font-bold flex items-center gap-1 ${
                  optimizationResult ? "text-emerald-700" : "text-slate-500"
                }`}
              >
                <Activity className="h-3 w-3 text-emerald-600" />
                {optimizationResult
                  ? optimizationResult.verification?.verified !== false
                    ? "Feasible & Verified"
                    : "Validation Warning"
                  : "Awaiting Run"}
              </span>
            </div>
          </Card>
        </div>

        {/* Bento Cell 3: Metrics Row (Col-span 12) */}
        <div className="col-span-1 md:col-span-2 lg:col-span-12">
          <OptimizationSummary result={optimizationResult} />
        </div>

        {/* Bento Cell 4: Scenario Form & Directives Input (Col-span 5) */}
        <div className="col-span-1 md:col-span-2 lg:col-span-5 space-y-5">
          <ScenarioForm onOptimized={setOptimizationResult} />
          <DirectivesCard
            directives={optimizationResult?.directive_interpretation}
            statusMessage={optimizationResult?.status_message}
          />
        </div>

        {/* Bento Cell 5: Demand vs Grid Import Chart (Col-span 7) */}
        <div className="col-span-1 md:col-span-2 lg:col-span-7">
          <DemandChart schedule={optimizationResult?.schedule} />
        </div>

        {/* Bento Cell 6: Solar Chart (Col-span 6) */}
        <div className="col-span-1 md:col-span-1 lg:col-span-6">
          <SolarChart schedule={optimizationResult?.schedule} />
        </div>

        {/* Bento Cell 7: Battery Chart (Col-span 6) */}
        <div className="col-span-1 md:col-span-1 lg:col-span-6">
          <BatteryChart schedule={optimizationResult?.schedule} />
        </div>

        {/* Bento Cell 8: 24-Hour Dispatch Matrix Data Grid (Col-span 12) */}
        <div className="col-span-1 md:col-span-2 lg:col-span-12">
          <ScheduleTable schedule={optimizationResult?.schedule} />
        </div>

      </div>
    </PageContainer>
  );
}

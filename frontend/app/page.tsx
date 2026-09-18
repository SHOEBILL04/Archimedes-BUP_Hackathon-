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
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Sparkles, Zap, Cpu, ShieldCheck, ArrowRight, Activity } from "lucide-react";
import Link from "next/link";
import { formatCurrencyBDT } from "@/lib/utils";

export default function HomePage() {
  const [optimizationResult, setOptimizationResult] =
    useState<OptimizationResponse | null>(null);

  const totalCost = optimizationResult?.total_grid_cost_bdt ?? 9852.0;

  return (
    <PageContainer title="Overview & Bento Console">
      {/* 12-Column Asymmetric Bento Grid Architecture */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-12 gap-5">
        
        {/* Bento Cell 1: Hero Focus Card (Col-span 8) */}
        <div className="md:col-span-2 lg:col-span-8">
          <div className="bento-card p-7 relative overflow-hidden h-full flex flex-col justify-between border-white/[0.08] hover:border-cyan-400/30 group">
            <div className="absolute -top-16 -right-16 w-64 h-64 bg-cyan-500/10 rounded-full blur-3xl pointer-events-none group-hover:bg-cyan-500/20 transition-all duration-500" />
            
            <div className="relative z-1 space-y-3">
              <div className="flex flex-wrap items-center gap-2">
                <Badge variant="cyan" className="font-mono gap-1.5 px-3 py-1">
                  <Sparkles className="h-3 w-3" />
                  <span>BUP CSE Fest 2026 Challenge</span>
                </Badge>
                <Badge variant="secondary" className="font-mono text-[10px]">
                  Archimedes Platform
                </Badge>
              </div>

              <h1 className="text-2xl sm:text-3xl font-extrabold text-white tracking-tight leading-tight">
                Smart Campus Energy <br className="hidden sm:inline" />
                <span className="bg-gradient-to-r from-cyan-400 via-sky-300 to-blue-400 bg-clip-text text-transparent">
                  Optimization Engine
                </span>
              </h1>

              <p className="text-xs sm:text-sm text-slate-400 leading-relaxed max-w-2xl">
                Multi-stage dispatch system coupling natural language operator directives with
                deterministic physical guardrails and PuLP/CBC linear programming to minimize
                grid electricity tariffs while guaranteeing battery longevity.
              </p>
            </div>

            <div className="relative z-1 pt-6 flex flex-wrap items-center justify-between gap-4 border-t border-white/[0.06] mt-4">
              <div className="flex flex-wrap items-center gap-4 text-xs font-mono text-slate-400">
                <div className="flex items-center gap-1.5 text-cyan-400">
                  <Zap className="h-3.5 w-3.5" />
                  <span>LP Solver</span>
                </div>
                <div className="flex items-center gap-1.5 text-sky-400">
                  <ShieldCheck className="h-3.5 w-3.5" />
                  <span>Replay Validator</span>
                </div>
                <div className="flex items-center gap-1.5 text-teal-400">
                  <Cpu className="h-3.5 w-3.5" />
                  <span>LLM Guardrails</span>
                </div>
              </div>

              <Link
                href="/dashboard"
                className="inline-flex items-center gap-1.5 text-xs font-semibold text-cyan-400 hover:text-cyan-300 transition-colors group/link font-mono"
              >
                <span>Full Workbench</span>
                <ArrowRight className="h-3.5 w-3.5 group-hover/link:translate-x-1 transition-transform" />
              </Link>
            </div>
          </div>
        </div>

        {/* Bento Cell 2: Primary Cost KPI Spotlight Card (Col-span 4) */}
        <div className="md:col-span-2 lg:col-span-4">
          <Card className="bento-card p-6 h-full flex flex-col justify-between border-white/[0.08] hover:border-cyan-400/30 group">
            <div className="absolute -bottom-10 -left-10 w-32 h-32 bg-cyan-500/10 rounded-full blur-2xl pointer-events-none group-hover:bg-cyan-500/20 transition-all" />
            
            <div className="flex items-center justify-between">
              <span className="text-[11px] font-mono text-slate-400 uppercase tracking-wider">
                Objective Function Value
              </span>
              <span className="h-2 w-2 rounded-full bg-cyan-400 animate-pulse" />
            </div>

            <div className="my-auto py-3">
              <span className="text-[11px] font-mono text-cyan-400 block mb-1">Total Grid Tariff</span>
              <h3 className="text-3xl sm:text-4xl font-extrabold font-mono text-white tracking-tight">
                {formatCurrencyBDT(totalCost)}
              </h3>
              <p className="text-[11px] text-slate-400 mt-2 font-mono">
                Evaluated across 24 hourly time-of-use bins
              </p>
            </div>

            <div className="pt-3 border-t border-white/[0.06] flex items-center justify-between text-[11px] font-mono">
              <span className="text-slate-400">Physical Balance:</span>
              <span className="text-cyan-400 font-semibold flex items-center gap-1">
                <Activity className="h-3 w-3" />
                Verified
              </span>
            </div>
          </Card>
        </div>

        {/* Bento Cell 3: Metrics Row (Col-span 12) */}
        <div className="col-span-1 md:col-span-2 lg:col-span-12">
          <OptimizationSummary result={optimizationResult} />
        </div>

        {/* Bento Cell 4: Scenario Form & Directives Input (Col-span 5) */}
        <div className="col-span-1 md:col-span-2 lg:col-span-5">
          <ScenarioForm onOptimized={setOptimizationResult} />
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

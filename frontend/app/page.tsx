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
      {/* 12-Column Asymmetric Bento Grid Architecture in Clean Light Theme */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-12 gap-5">
        
        {/* Bento Cell 1: Hero Focus Card (Soft Warm Cream Accent Background #FFF6DC) */}
        <div className="md:col-span-2 lg:col-span-8">
          <div className="bento-card bento-card-warm p-7 relative overflow-hidden h-full flex flex-col justify-between border-[#f5e4ab] hover:border-[#425B9A]/40 group">
            <div className="space-y-3">
              <div className="flex flex-wrap items-center gap-2">
                <Badge variant="indigo" className="font-mono gap-1.5 px-3 py-1">
                  <Sparkles className="h-3 w-3" />
                  <span>BUP CSE Fest 2026 Challenge</span>
                </Badge>
                <Badge variant="coral" className="font-mono text-[10px]">
                  Archimedes Platform
                </Badge>
              </div>

              <h1 className="text-2xl sm:text-3xl font-extrabold text-[#425B9A] tracking-tight leading-tight">
                Smart Campus Energy <br className="hidden sm:inline" />
                <span className="text-[#1E293B]">Optimization Platform</span>
              </h1>

              <p className="text-xs sm:text-sm text-slate-700 leading-relaxed max-w-2xl font-medium">
                Multi-stage dispatch system coupling natural language operator directives with
                deterministic physical guardrails and PuLP/CBC linear programming to minimize
                grid electricity tariffs while guaranteeing battery longevity.
              </p>
            </div>

            <div className="pt-6 flex flex-wrap items-center justify-between gap-4 border-t border-[#f5e4ab]/80 mt-4">
              <div className="flex flex-wrap items-center gap-4 text-xs font-mono font-semibold text-slate-600">
                <div className="flex items-center gap-1.5 text-[#425B9A]">
                  <Zap className="h-3.5 w-3.5" />
                  <span>LP Solver</span>
                </div>
                <div className="flex items-center gap-1.5 text-[#254b7c]">
                  <ShieldCheck className="h-3.5 w-3.5 text-[#76C0EC]" />
                  <span>Replay Validator</span>
                </div>
                <div className="flex items-center gap-1.5 text-[#78590c]">
                  <Cpu className="h-3.5 w-3.5" />
                  <span>LLM Guardrails</span>
                </div>
              </div>

              <Link
                href="/dashboard"
                className="inline-flex items-center gap-1.5 text-xs font-bold text-[#425B9A] hover:text-[#314474] transition-colors group/link font-mono"
              >
                <span>Full Workbench</span>
                <ArrowRight className="h-3.5 w-3.5 group-hover/link:translate-x-1 transition-transform" />
              </Link>
            </div>
          </div>
        </div>

        {/* Bento Cell 2: Primary Cost KPI Spotlight Card */}
        <div className="md:col-span-2 lg:col-span-4">
          <Card className="bento-card p-6 h-full flex flex-col justify-between border-slate-200/90 hover:border-[#425B9A]/30 group">
            <div className="flex items-center justify-between">
              <span className="text-[11px] font-mono font-bold text-slate-500 uppercase tracking-wider">
                Objective Function Value
              </span>
              <span className="h-2.5 w-2.5 rounded-full bg-[#76C0EC] ring-4 ring-[#76C0EC]/30" />
            </div>

            <div className="my-auto py-3">
              <span className="text-[11px] font-mono font-bold text-[#425B9A] block mb-1">Total Grid Tariff</span>
              <h3 className="text-3xl sm:text-4xl font-extrabold font-mono text-[#1E293B] tracking-tight">
                {formatCurrencyBDT(totalCost)}
              </h3>
              <p className="text-[11px] text-slate-500 mt-2 font-mono">
                Evaluated across 24 hourly time-of-use bins
              </p>
            </div>

            <div className="pt-3 border-t border-slate-100 flex items-center justify-between text-[11px] font-mono">
              <span className="text-slate-500">Physical Balance:</span>
              <span className="text-[#425B9A] font-bold flex items-center gap-1">
                <Activity className="h-3 w-3 text-[#76C0EC]" />
                Feasible & Verified
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

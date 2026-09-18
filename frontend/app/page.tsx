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
import { Zap, Cpu, Sparkles } from "lucide-react";

export default function HomePage() {
  const [optimizationResult, setOptimizationResult] =
    useState<OptimizationResponse | null>(null);

  return (
    <PageContainer title="Overview & Dispatch Console">
      {/* Hero Welcome Banner */}
      <div className="relative overflow-hidden rounded-2xl border border-slate-800 bg-gradient-to-r from-slate-900 via-slate-900/90 to-emerald-950/40 p-8 shadow-2xl">
        <div className="absolute top-0 right-0 -mt-8 -mr-8 w-64 h-64 bg-emerald-500/10 rounded-full blur-3xl pointer-events-none" />
        <div className="relative z-1 max-w-3xl space-y-3">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full text-xs font-semibold bg-emerald-500/15 text-emerald-400 border border-emerald-500/30">
            <Sparkles className="h-3.5 w-3.5" />
            <span>BUP CSE Fest 2026 Challenge</span>
          </div>
          <h1 className="text-3xl font-extrabold text-white tracking-tight sm:text-4xl">
            Smart Campus Energy Optimization Platform
          </h1>
          <p className="text-sm sm:text-base text-slate-300 leading-relaxed">
            Multi-stage energy dispatch engine combining natural-language operator note
            interpretation, deterministic physical guardrails, and PuLP/CBC linear
            programming to minimize grid tariff costs and maximize solar battery efficiency.
          </p>

          <div className="flex flex-wrap items-center gap-6 pt-2 text-xs text-slate-400">
            <div className="flex items-center gap-2">
              <Zap className="h-4 w-4 text-emerald-400" />
              <span>Linear Programming Dispatch</span>
            </div>
            <div className="flex items-center gap-2">
              <Cpu className="h-4 w-4 text-teal-400" />
              <span>Deterministic Replay Validation</span>
            </div>
          </div>
        </div>
      </div>

      {/* KPI Summary Cards */}
      <section className="space-y-3">
        <h2 className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
          Executive Dispatch Metrics
        </h2>
        <OptimizationSummary result={optimizationResult} />
      </section>

      {/* Interactive Scenario Input Form */}
      <section className="space-y-3">
        <h2 className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
          Dispatch Configuration
        </h2>
        <ScenarioForm onOptimized={setOptimizationResult} />
      </section>

      {/* Charts Section */}
      <section className="space-y-3">
        <h2 className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
          Telemetry & Load Analytics
        </h2>
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <DemandChart schedule={optimizationResult?.schedule} />
          <SolarChart schedule={optimizationResult?.schedule} />
        </div>
        <div className="pt-2">
          <BatteryChart schedule={optimizationResult?.schedule} />
        </div>
      </section>

      {/* Hourly Schedule Table */}
      <section className="space-y-3">
        <h2 className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
          24-Hour Schedule Matrix
        </h2>
        <ScheduleTable schedule={optimizationResult?.schedule} />
      </section>
    </PageContainer>
  );
}

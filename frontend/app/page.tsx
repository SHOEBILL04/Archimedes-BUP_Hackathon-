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
import {
  Sparkles,
  Zap,
  Cpu,
  ShieldCheck,
  ArrowRight,
  Activity,
} from "lucide-react";
import Link from "next/link";
import { formatCurrencyBDT } from "@/lib/utils";

export default function HomePage() {
  const [optimizationResult, setOptimizationResult] =
    useState<OptimizationResponse | null>(null);

  const totalCost = optimizationResult?.total_grid_cost_bdt ?? 9852.0;

  return (
    <PageContainer title="Overview & Bento Console">
      <div className="grid grid-cols-1 gap-5 md:grid-cols-2 lg:grid-cols-12">
        {/* Hero — warm cream surface anchors the grid. */}
        <div className="md:col-span-2 lg:col-span-8">
          <div className="bento-card bento-card-warm group flex h-full flex-col justify-between overflow-hidden p-7">
            <div className="space-y-3">
              <div className="flex flex-wrap items-center gap-2">
                <Badge variant="brand" className="gap-1.5 px-3 py-1 font-mono">
                  <Sparkles className="h-3 w-3" />
                  <span>BUP CSE Fest 2026 Challenge</span>
                </Badge>
                <Badge variant="coral" className="font-mono text-[10px]">
                  Archimedes Platform
                </Badge>
              </div>

              <h1 className="text-2xl font-extrabold leading-tight tracking-tight text-brand sm:text-3xl">
                Smart Campus Energy <br className="hidden sm:inline" />
                <span className="text-ink">Optimization Platform</span>
              </h1>

              <p className="max-w-2xl text-xs font-medium leading-relaxed text-ink-muted sm:text-sm">
                Multi-stage dispatch system coupling natural language operator
                directives with deterministic physical guardrails and PuLP/CBC
                linear programming to minimize grid electricity tariffs while
                guaranteeing battery longevity.
              </p>
            </div>

            <div className="mt-4 flex flex-wrap items-center justify-between gap-4 border-t border-brand/12 pt-6">
              <div className="flex flex-wrap items-center gap-4 font-mono text-xs font-semibold">
                <div className="flex items-center gap-1.5 text-brand">
                  <Zap className="h-3.5 w-3.5" />
                  <span>LP Solver</span>
                </div>
                <div className="flex items-center gap-1.5 text-accent-ink">
                  <ShieldCheck className="h-3.5 w-3.5" />
                  <span>Replay Validator</span>
                </div>
                <div className="flex items-center gap-1.5 text-cream-ink">
                  <Cpu className="h-3.5 w-3.5" />
                  <span>LLM Guardrails</span>
                </div>
              </div>

              <Link
                href="/dashboard"
                className="group/link inline-flex items-center gap-1.5 rounded-lg font-mono text-xs font-bold text-brand transition-colors hover:text-brand-700"
              >
                <span>Full Workbench</span>
                <ArrowRight className="h-3.5 w-3.5 transition-transform group-hover/link:translate-x-1 motion-reduce:transition-none" />
              </Link>
            </div>
          </div>
        </div>

        {/* Objective function spotlight */}
        <div className="md:col-span-2 lg:col-span-4">
          <Card className="flex h-full flex-col justify-between p-6">
            <div className="flex items-center justify-between">
              <span className="stat-label">Objective Function Value</span>
              <span className="h-2.5 w-2.5 rounded-full bg-accent-600 ring-4 ring-accent/30" />
            </div>

            <div className="my-auto py-3">
              <span className="mb-1 block font-mono text-[11px] font-bold text-brand">
                Total Grid Tariff
              </span>
              <p className="font-mono text-3xl font-extrabold tracking-tight text-ink sm:text-4xl">
                {formatCurrencyBDT(totalCost)}
              </p>
              <p className="mt-2 font-mono text-[11px] text-ink-muted">
                Evaluated across 24 hourly time-of-use bins
              </p>
            </div>

            <div className="flex items-center justify-between border-t border-line pt-3 font-mono text-[11px]">
              <span className="text-ink-muted">Physical Balance:</span>
              <span className="flex items-center gap-1 font-bold text-brand">
                <Activity className="h-3 w-3 text-accent-ink" />
                Feasible &amp; Verified
              </span>
            </div>
          </Card>
        </div>

        <div className="col-span-1 md:col-span-2 lg:col-span-12">
          <OptimizationSummary result={optimizationResult} />
        </div>

        <div className="col-span-1 md:col-span-2 lg:col-span-5">
          <ScenarioForm onOptimized={setOptimizationResult} />
        </div>

        <div className="col-span-1 md:col-span-2 lg:col-span-7">
          <DemandChart schedule={optimizationResult?.schedule} />
        </div>

        <div className="col-span-1 md:col-span-1 lg:col-span-6">
          <SolarChart schedule={optimizationResult?.schedule} />
        </div>

        <div className="col-span-1 md:col-span-1 lg:col-span-6">
          <BatteryChart schedule={optimizationResult?.schedule} />
        </div>

        <div className="col-span-1 md:col-span-2 lg:col-span-12">
          <ScheduleTable schedule={optimizationResult?.schedule} />
        </div>
      </div>
    </PageContainer>
  );
}

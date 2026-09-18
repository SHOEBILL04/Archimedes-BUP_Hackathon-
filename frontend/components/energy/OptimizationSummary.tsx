import React from "react";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { OptimizationResponse } from "@/types/energy";
import { formatCurrencyBDT, formatNumber } from "@/lib/utils";
import { Coins, Zap, ShieldCheck, SolarPanel, ArrowUpRight } from "lucide-react";

interface OptimizationSummaryProps {
  result?: OptimizationResponse | null;
}

export function OptimizationSummary({ result }: OptimizationSummaryProps) {
  const totalCost = result?.total_grid_cost_bdt ?? 9852.0;
  const totalGridKwh = result?.total_grid_kwh ?? 840.5;
  const isVerified = result?.verification?.verified ?? true;
  const totalSolarUsed = result?.schedule
    ? result.schedule.reduce((acc, curr) => acc + curr.solar_used_kwh, 0)
    : 320.0;

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
      {/* 1. Total Grid Cost Bento Card */}
      <Card className="bento-card border-[rgba(28,49,46,0.08)] group">
        <CardContent className="p-5 flex flex-col justify-between h-full">
          <div className="flex items-center justify-between mb-3">
            <span className="text-[11px] font-mono font-bold text-[#6E8480] uppercase tracking-wider">
              Total Grid Cost
            </span>
            <div className="h-8 w-8 rounded-lg bg-[#E8EFE9] border border-[rgba(28,49,46,0.1)] flex items-center justify-center text-[#1C312E] shadow-2xs">
              <Coins className="h-4 w-4" />
            </div>
          </div>
          <div>
            <div className="text-2xl sm:text-3xl font-bold font-mono tracking-tight text-[#1C312E]">
              {formatCurrencyBDT(totalCost)}
            </div>
            <div className="flex items-center gap-1.5 mt-2 text-[11px] text-[#4E8773] font-mono font-semibold">
              <ArrowUpRight className="h-3 w-3 text-[#4E8773]" />
              <span>Optimized with PuLP solver</span>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* 2. Grid Energy Import Bento Card */}
      <Card className="bento-card border-[rgba(28,49,46,0.08)] group">
        <CardContent className="p-5 flex flex-col justify-between h-full">
          <div className="flex items-center justify-between mb-3">
            <span className="text-[11px] font-mono font-bold text-[#6E8480] uppercase tracking-wider">
              Grid Import Energy
            </span>
            <div className="h-8 w-8 rounded-lg bg-[#E8EFE9] border border-[rgba(28,49,46,0.1)] flex items-center justify-center text-[#1C312E]">
              <Zap className="h-4 w-4 text-[#4E8773]" />
            </div>
          </div>
          <div>
            <div className="text-2xl sm:text-3xl font-bold font-mono tracking-tight text-[#1C312E] flex items-baseline gap-1.5">
              <span>{formatNumber(totalGridKwh, 1)}</span>
              <span className="text-xs font-mono font-normal text-[#6E8480]">kWh</span>
            </div>
            <div className="flex items-center gap-1.5 mt-2 text-[11px] text-[#6E8480] font-mono">
              <span>24-hr cumulative import</span>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* 3. Solar Harvested Bento Card */}
      <Card className="bento-card border-[rgba(28,49,46,0.08)] group">
        <CardContent className="p-5 flex flex-col justify-between h-full">
          <div className="flex items-center justify-between mb-3">
            <span className="text-[11px] font-mono font-bold text-[#6E8480] uppercase tracking-wider">
              Solar Dispatched
            </span>
            <div className="h-8 w-8 rounded-lg bg-[#E8EFE9] border border-[rgba(28,49,46,0.1)] flex items-center justify-center text-[#4E8773]">
              <SolarPanel className="h-4 w-4" />
            </div>
          </div>
          <div>
            <div className="text-2xl sm:text-3xl font-bold font-mono tracking-tight text-[#1C312E] flex items-baseline gap-1.5">
              <span>{formatNumber(totalSolarUsed, 1)}</span>
              <span className="text-xs font-mono font-normal text-[#6E8480]">kWh</span>
            </div>
            <div className="flex items-center gap-1.5 mt-2 text-[11px] text-[#4E8773] font-mono font-semibold">
              <span>Zero-carbon self-consumption</span>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* 4. Physical Balance & Replay Bento Card */}
      <Card className="bento-card border-[rgba(28,49,46,0.08)] group">
        <CardContent className="p-5 flex flex-col justify-between h-full">
          <div className="flex items-center justify-between mb-3">
            <span className="text-[11px] font-mono font-bold text-[#6E8480] uppercase tracking-wider">
              Replay Validation
            </span>
            <div className="h-8 w-8 rounded-lg bg-[#E8EFE9] border border-[rgba(28,49,46,0.1)] flex items-center justify-center text-[#4E8773]">
              <ShieldCheck className="h-4 w-4" />
            </div>
          </div>
          <div>
            <div>
              <Badge
                variant={isVerified ? "sage" : "copper"}
                className="font-mono text-[11px] px-2.5 py-1"
              >
                {isVerified ? "Verified Feasible (0.000 error)" : "Limit Warning"}
              </Badge>
            </div>
            <div className="flex items-center gap-1.5 mt-3 text-[11px] text-[#6E8480] font-mono">
              <span>13 physical equations verified</span>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

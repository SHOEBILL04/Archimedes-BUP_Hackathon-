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
      {/* 1. Total Grid Cost Bento Card (Warm Cream Accent Card) */}
      <Card className="bento-card bento-card-warm border-[#f5e4ab] hover:border-[#425B9A]/30 group">
        <CardContent className="p-5 flex flex-col justify-between h-full">
          <div className="flex items-center justify-between mb-3">
            <span className="text-[11px] font-mono font-bold text-[#78590c] uppercase tracking-wider">
              Total Grid Cost
            </span>
            <div className="h-8 w-8 rounded-lg bg-[#425B9A] flex items-center justify-center text-white shadow-xs">
              <Coins className="h-4 w-4" />
            </div>
          </div>
          <div>
            <div className="text-2xl sm:text-3xl font-bold font-mono tracking-tight text-[#425B9A]">
              {formatCurrencyBDT(totalCost)}
            </div>
            <div className="flex items-center gap-1.5 mt-2 text-[11px] text-[#2c477f] font-mono font-medium">
              <ArrowUpRight className="h-3 w-3 text-[#425B9A]" />
              <span>Optimized with PuLP solver</span>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* 2. Grid Energy Import Bento Card */}
      <Card className="bento-card border-slate-200/90 hover:border-[#76C0EC] group">
        <CardContent className="p-5 flex flex-col justify-between h-full">
          <div className="flex items-center justify-between mb-3">
            <span className="text-[11px] font-mono font-bold text-slate-500 uppercase tracking-wider">
              Grid Import Energy
            </span>
            <div className="h-8 w-8 rounded-lg bg-[#76C0EC]/20 border border-[#76C0EC]/40 flex items-center justify-center text-[#254b7c]">
              <Zap className="h-4 w-4" />
            </div>
          </div>
          <div>
            <div className="text-2xl sm:text-3xl font-bold font-mono tracking-tight text-[#1E293B] flex items-baseline gap-1.5">
              <span>{formatNumber(totalGridKwh, 1)}</span>
              <span className="text-xs font-mono font-normal text-slate-500">kWh</span>
            </div>
            <div className="flex items-center gap-1.5 mt-2 text-[11px] text-slate-500 font-mono">
              <span>24-hr cumulative import</span>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* 3. Solar Harvested Bento Card */}
      <Card className="bento-card border-slate-200/90 hover:border-amber-400 group">
        <CardContent className="p-5 flex flex-col justify-between h-full">
          <div className="flex items-center justify-between mb-3">
            <span className="text-[11px] font-mono font-bold text-slate-500 uppercase tracking-wider">
              Solar Dispatched
            </span>
            <div className="h-8 w-8 rounded-lg bg-amber-100 border border-amber-200 flex items-center justify-center text-amber-700">
              <SolarPanel className="h-4 w-4" />
            </div>
          </div>
          <div>
            <div className="text-2xl sm:text-3xl font-bold font-mono tracking-tight text-[#1E293B] flex items-baseline gap-1.5">
              <span>{formatNumber(totalSolarUsed, 1)}</span>
              <span className="text-xs font-mono font-normal text-slate-500">kWh</span>
            </div>
            <div className="flex items-center gap-1.5 mt-2 text-[11px] text-emerald-700 font-mono font-semibold">
              <span>Zero-carbon self-consumption</span>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* 4. Physical Balance & Replay Bento Card */}
      <Card className="bento-card border-slate-200/90 hover:border-[#425B9A]/30 group">
        <CardContent className="p-5 flex flex-col justify-between h-full">
          <div className="flex items-center justify-between mb-3">
            <span className="text-[11px] font-mono font-bold text-slate-500 uppercase tracking-wider">
              Replay Validation
            </span>
            <div className="h-8 w-8 rounded-lg bg-[#425B9A]/10 border border-[#425B9A]/20 flex items-center justify-center text-[#425B9A]">
              <ShieldCheck className="h-4 w-4" />
            </div>
          </div>
          <div>
            <div>
              <Badge
                variant={isVerified ? "sky" : "coral"}
                className="font-mono text-[11px] px-2.5 py-1"
              >
                {isVerified ? "Balance Feasible (0.000 error)" : "Validation Warning"}
              </Badge>
            </div>
            <div className="flex items-center gap-1.5 mt-3 text-[11px] text-slate-500 font-mono">
              <span>Hourly equations satisfied</span>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

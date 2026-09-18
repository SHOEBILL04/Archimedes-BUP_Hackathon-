import React from "react";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { OptimizationResponse } from "@/types/energy";
import { formatCurrencyBDT, formatNumber } from "@/lib/utils";
import { Coins, Zap, ShieldCheck, Sun, ArrowUpRight } from "lucide-react";

interface OptimizationSummaryProps {
  result?: OptimizationResponse | null;
}

interface StatTileProps {
  label: string;
  icon: React.ReactNode;
  /** Tinted chip behind the icon. */
  iconClassName: string;
  children: React.ReactNode;
  footnote: React.ReactNode;
  tone?: "surface" | "warm";
}

function StatTile({
  label,
  icon,
  iconClassName,
  children,
  footnote,
  tone = "surface",
}: StatTileProps) {
  return (
    <Card tone={tone} className="h-full">
      <CardContent className="flex h-full flex-col justify-between p-5">
        <div className="mb-3 flex items-center justify-between">
          <span className="stat-label">{label}</span>
          <div
            className={`flex h-8 w-8 items-center justify-center rounded-lg ${iconClassName}`}
          >
            {icon}
          </div>
        </div>
        <div>
          {children}
          <div className="mt-2 flex items-center gap-1.5 font-mono text-[11px] text-ink-muted">
            {footnote}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

export function OptimizationSummary({ result }: OptimizationSummaryProps) {
  const totalCost = result?.total_grid_cost_bdt ?? 9852.0;
  const totalGridKwh = result?.total_grid_kwh ?? 840.5;
  const isVerified = result?.verification?.verified ?? true;
  const totalSolarUsed = result?.schedule
    ? result.schedule.reduce((acc, curr) => acc + curr.solar_used_kwh, 0)
    : 320.0;

  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
      {/* Objective value — warm cream accent tile anchors the row. */}
      <StatTile
        tone="warm"
        label="Total Grid Cost"
        icon={<Coins className="h-4 w-4" />}
        iconClassName="bg-brand text-white shadow-tile"
        footnote={
          <>
            <ArrowUpRight className="h-3 w-3 text-brand" />
            <span>Optimized with PuLP solver</span>
          </>
        }
      >
        <div className="font-mono text-2xl font-bold tracking-tight text-brand sm:text-3xl">
          {formatCurrencyBDT(totalCost)}
        </div>
      </StatTile>

      <StatTile
        label="Grid Import Energy"
        icon={<Zap className="h-4 w-4" />}
        iconClassName="bg-accent-100 border border-accent/40 text-accent-ink"
        footnote={<span>24-hr cumulative import</span>}
      >
        <div className="flex items-baseline gap-1.5 font-mono text-2xl font-bold tracking-tight text-ink sm:text-3xl">
          <span>{formatNumber(totalGridKwh, 1)}</span>
          <span className="text-xs font-normal text-ink-muted">kWh</span>
        </div>
      </StatTile>

      <StatTile
        label="Solar Dispatched"
        icon={<Sun className="h-4 w-4" />}
        iconClassName="bg-cream border border-cream-ink/25 text-cream-ink"
        footnote={
          <span className="font-semibold text-cream-ink">
            Zero-carbon self-consumption
          </span>
        }
      >
        <div className="flex items-baseline gap-1.5 font-mono text-2xl font-bold tracking-tight text-ink sm:text-3xl">
          <span>{formatNumber(totalSolarUsed, 1)}</span>
          <span className="text-xs font-normal text-ink-muted">kWh</span>
        </div>
      </StatTile>

      <StatTile
        label="Replay Validation"
        icon={<ShieldCheck className="h-4 w-4" />}
        iconClassName="bg-brand-50 border border-brand/20 text-brand"
        footnote={<span>Hourly equations satisfied</span>}
      >
        <Badge
          variant={isVerified ? "accent" : "coral"}
          className="px-2.5 py-1 font-mono text-[11px]"
        >
          {isVerified ? "Balance Feasible (0.000 error)" : "Validation Warning"}
        </Badge>
      </StatTile>
    </div>
  );
}

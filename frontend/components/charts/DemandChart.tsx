"use client";

import React from "react";
import { HourSchedule } from "@/types/energy";
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from "recharts";
import { Activity } from "lucide-react";
import { ChartFrame } from "./ChartFrame";
import { HOURS_IN_HORIZON } from "@/lib/constants";
import {
  palette,
  seriesColor,
  chartAxis,
  chartGrid,
  chartTooltipStyle,
  chartLegendStyle,
} from "@/lib/design/tokens";

interface DemandChartProps {
  schedule?: HourSchedule[];
}

export function DemandChart({ schedule }: DemandChartProps) {
  const chartData =
    schedule && schedule.length === HOURS_IN_HORIZON
      ? schedule.map((item) => ({
          hour: `${String(item.hour).padStart(2, "0")}:00`,
          demand: item.demand_kwh,
          grid: item.grid_kwh,
        }))
      : Array.from({ length: HOURS_IN_HORIZON }, (_, i) => ({
          hour: `${String(i).padStart(2, "0")}:00`,
          demand: 35 + Math.sin(i / 3) * 15,
          grid: 25 + Math.sin(i / 3) * 10,
        }));

  return (
    <ChartFrame
      title="Campus Demand vs. Grid Import"
      description="Hourly comparison between gross campus energy demand and grid import."
      icon={<Activity className="h-4 w-4" />}
      action={
        <span className="hidden rounded-md border border-brand/20 bg-brand-50 px-2 py-0.5 font-mono text-[10px] font-bold text-brand sm:inline-block">
          24h Profile
        </span>
      }
    >
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart
          data={chartData}
          margin={{ top: 10, right: 10, left: -20, bottom: 0 }}
        >
          <defs>
            {/* Pastels carry the area fills; the stroke above them carries the data. */}
            <linearGradient id="demandFill" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor={palette.accent} stopOpacity={0.45} />
              <stop offset="95%" stopColor={palette.accent} stopOpacity={0.05} />
            </linearGradient>
            <linearGradient id="gridFill" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor={palette.brand} stopOpacity={0.3} />
              <stop offset="95%" stopColor={palette.brand} stopOpacity={0.02} />
            </linearGradient>
          </defs>
          <CartesianGrid {...chartGrid} />
          <XAxis dataKey="hour" {...chartAxis} />
          <YAxis {...chartAxis} />
          <Tooltip
            contentStyle={chartTooltipStyle}
            cursor={{ stroke: palette.brandLight, strokeWidth: 1 }}
          />
          <Legend wrapperStyle={chartLegendStyle} />
          <Area
            type="monotone"
            dataKey="demand"
            name="Gross Demand (kWh)"
            stroke={seriesColor.demand}
            strokeWidth={2}
            fillOpacity={1}
            fill="url(#demandFill)"
          />
          <Area
            type="monotone"
            dataKey="grid"
            name="Grid Dispatched (kWh)"
            stroke={seriesColor.grid}
            strokeWidth={2.5}
            fillOpacity={1}
            fill="url(#gridFill)"
          />
        </AreaChart>
      </ResponsiveContainer>
    </ChartFrame>
  );
}

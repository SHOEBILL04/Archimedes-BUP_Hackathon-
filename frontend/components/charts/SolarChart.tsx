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
import { Sun } from "lucide-react";
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

interface SolarChartProps {
  schedule?: HourSchedule[];
}

export function SolarChart({ schedule }: SolarChartProps) {
  const chartData =
    schedule && schedule.length === HOURS_IN_HORIZON
      ? schedule.map((item) => ({
          hour: `${String(item.hour).padStart(2, "0")}:00`,
          effective_solar: item.effective_solar_kwh,
          solar_used: item.solar_used_kwh,
        }))
      : Array.from({ length: HOURS_IN_HORIZON }, (_, i) => ({
          hour: `${String(i).padStart(2, "0")}:00`,
          effective_solar:
            i >= 6 && i <= 17 ? Math.sin(((i - 6) / 11) * Math.PI) * 40 : 0,
          solar_used:
            i >= 6 && i <= 17 ? Math.sin(((i - 6) / 11) * Math.PI) * 35 : 0,
        }));

  return (
    <ChartFrame
      title="Solar Generation & Utilization"
      description="Photovoltaic baseline vs. real-time energy directed into campus loads."
      icon={<Sun className="h-4 w-4 text-cream-ink" />}
    >
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart
          data={chartData}
          margin={{ top: 10, right: 10, left: -20, bottom: 0 }}
        >
          <defs>
            <linearGradient id="solarPotentialFill" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor={palette.cream} stopOpacity={1} />
              <stop offset="95%" stopColor={palette.cream} stopOpacity={0.1} />
            </linearGradient>
            <linearGradient id="solarUsedFill" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor={palette.accent} stopOpacity={0.5} />
              <stop offset="95%" stopColor={palette.accent} stopOpacity={0.05} />
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
            dataKey="effective_solar"
            name="Potential Solar (kWh)"
            stroke={seriesColor.solarPotential}
            strokeWidth={1.5}
            strokeDasharray="4 3"
            fillOpacity={1}
            fill="url(#solarPotentialFill)"
          />
          <Area
            type="monotone"
            dataKey="solar_used"
            name="Dispatched Solar (kWh)"
            stroke={seriesColor.solarDispatched}
            strokeWidth={2}
            fillOpacity={1}
            fill="url(#solarUsedFill)"
          />
        </AreaChart>
      </ResponsiveContainer>
    </ChartFrame>
  );
}

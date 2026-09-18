"use client";

import React from "react";
import { HourSchedule } from "@/types/energy";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from "recharts";
import { BatteryCharging } from "lucide-react";
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

interface BatteryChartProps {
  schedule?: HourSchedule[];
}

export function BatteryChart({ schedule }: BatteryChartProps) {
  const chartData =
    schedule && schedule.length === HOURS_IN_HORIZON
      ? schedule.map((item) => ({
          hour: `${String(item.hour).padStart(2, "0")}:00`,
          soc: item.battery_energy_after_kwh,
          charge: item.battery_charge_kwh,
          discharge: item.battery_discharge_kwh,
        }))
      : Array.from({ length: HOURS_IN_HORIZON }, (_, i) => ({
          hour: `${String(i).padStart(2, "0")}:00`,
          soc: 40 + Math.sin(i / 4) * 20,
          charge: i >= 10 && i <= 14 ? 15 : 0,
          discharge: i >= 18 && i <= 21 ? 15 : 0,
        }));

  return (
    <ChartFrame
      title="Battery State of Charge & Cycling"
      description="Energy stored in battery reserve (kWh) and active charge / discharge hourly cycles."
      icon={<BatteryCharging className="h-4 w-4" />}
    >
      <ResponsiveContainer width="100%" height="100%">
        <LineChart
          data={chartData}
          margin={{ top: 10, right: 10, left: -20, bottom: 0 }}
        >
          <CartesianGrid {...chartGrid} />
          <XAxis dataKey="hour" {...chartAxis} />
          <YAxis {...chartAxis} />
          <Tooltip
            contentStyle={chartTooltipStyle}
            cursor={{ stroke: palette.brandLight, strokeWidth: 1 }}
          />
          <Legend wrapperStyle={chartLegendStyle} />
          <Line
            type="monotone"
            dataKey="soc"
            name="Battery SoC (kWh)"
            stroke={seriesColor.batterySoc}
            strokeWidth={2.5}
            dot={false}
          />
          <Line
            type="step"
            dataKey="charge"
            name="Charge Power (kW)"
            stroke={seriesColor.charge}
            strokeWidth={1.8}
            dot={false}
          />
          <Line
            type="step"
            dataKey="discharge"
            name="Discharge Power (kW)"
            stroke={seriesColor.discharge}
            strokeWidth={2}
            dot={false}
          />
        </LineChart>
      </ResponsiveContainer>
    </ChartFrame>
  );
}

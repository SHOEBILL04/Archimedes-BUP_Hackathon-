"use client";

import React from "react";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/card";
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

interface BatteryChartProps {
  schedule?: HourSchedule[];
}

export function BatteryChart({ schedule }: BatteryChartProps) {
  const chartData =
    schedule && schedule.length === 24
      ? schedule.map((item) => ({
          hour: `${String(item.hour).padStart(2, "0")}:00`,
          soc: item.battery_energy_after_kwh,
          charge: item.battery_charge_kwh,
          discharge: item.battery_discharge_kwh,
        }))
      : Array.from({ length: 24 }, (_, i) => ({
          hour: `${String(i).padStart(2, "0")}:00`,
          soc: 40 + Math.sin(i / 4) * 20,
          charge: i >= 10 && i <= 14 ? 15 : 0,
          discharge: i >= 18 && i <= 21 ? 15 : 0,
        }));

  return (
    <Card className="bento-card border-white/[0.08] hover:border-cyan-400/30 h-full flex flex-col justify-between">
      <CardHeader className="p-6 pb-2">
        <div className="flex items-center justify-between">
          <div className="space-y-1">
            <CardTitle className="flex items-center gap-2 text-sm font-semibold text-white">
              <BatteryCharging className="h-4 w-4 text-cyan-400" />
              <span>Battery State of Charge & Cycling</span>
            </CardTitle>
            <CardDescription className="text-xs text-slate-400">
              Energy stored in battery reserve (kWh) and active charge / discharge hourly cycles.
            </CardDescription>
          </div>
        </div>
      </CardHeader>
      <CardContent className="p-6 pt-2 flex-1">
        <div className="h-[280px] w-full">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={chartData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
              <XAxis dataKey="hour" stroke="#64748b" fontSize={10} tickLine={false} />
              <YAxis stroke="#64748b" fontSize={10} tickLine={false} />
              <Tooltip
                contentStyle={{
                  backgroundColor: "#070b16",
                  borderColor: "rgba(255, 255, 255, 0.1)",
                  borderRadius: "12px",
                  fontSize: "11px",
                  fontFamily: "monospace",
                  boxShadow: "0 10px 25px -5px rgba(0, 0, 0, 0.6)",
                }}
              />
              <Legend wrapperStyle={{ fontSize: "11px", fontFamily: "monospace", paddingTop: "8px" }} />
              <Line
                type="monotone"
                dataKey="soc"
                name="Battery SoC (kWh)"
                stroke="#00f0ff"
                strokeWidth={2.5}
                dot={false}
              />
              <Line
                type="step"
                dataKey="charge"
                name="Charge (kW)"
                stroke="#38bdf8"
                strokeWidth={1.5}
                dot={false}
              />
              <Line
                type="step"
                dataKey="discharge"
                name="Discharge (kW)"
                stroke="#f43f5e"
                strokeWidth={1.5}
                dot={false}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </CardContent>
    </Card>
  );
}

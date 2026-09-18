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
    <Card className="bento-card border-[rgba(28,49,46,0.08)] h-full flex flex-col justify-between">
      <CardHeader className="p-6 pb-2">
        <div className="flex items-center justify-between">
          <div className="space-y-1">
            <CardTitle className="flex items-center gap-2 text-sm font-bold text-[#1C312E]">
              <BatteryCharging className="h-4 w-4 text-[#D97757]" />
              <span>Battery State of Charge & Cycling</span>
            </CardTitle>
            <CardDescription className="text-xs text-[#6E8480]">
              Energy stored in battery reserve (kWh) and active charge / discharge hourly cycles.
            </CardDescription>
          </div>
        </div>
      </CardHeader>
      <CardContent className="p-6 pt-2 flex-1">
        <div className="h-[280px] w-full">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={chartData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#E8EFE9" />
              <XAxis dataKey="hour" stroke="#6E8480" fontSize={10} tickLine={false} />
              <YAxis stroke="#6E8480" fontSize={10} tickLine={false} />
              <Tooltip
                contentStyle={{
                  backgroundColor: "#FFFFFF",
                  borderColor: "rgba(28,49,46,0.12)",
                  borderRadius: "12px",
                  fontSize: "11px",
                  fontFamily: "monospace",
                  color: "#1C312E",
                  boxShadow: "0 8px 24px -4px rgba(28,49,46,0.08)",
                }}
              />
              <Legend wrapperStyle={{ fontSize: "11px", fontFamily: "monospace", paddingTop: "8px" }} />
              <Line
                type="monotone"
                dataKey="soc"
                name="Battery SoC (kWh)"
                stroke="#1C312E"
                strokeWidth={2.5}
                dot={false}
              />
              <Line
                type="step"
                dataKey="charge"
                name="Charge Input (kW)"
                stroke="#4E8773"
                strokeWidth={2}
                dot={false}
              />
              <Line
                type="step"
                dataKey="discharge"
                name="Discharge Output (kW)"
                stroke="#D97757"
                strokeWidth={2}
                dot={false}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </CardContent>
    </Card>
  );
}

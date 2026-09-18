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
    <Card className="border-slate-800 bg-slate-900/50">
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-base">
          <BatteryCharging className="h-5 w-5 text-emerald-400" />
          <span>Battery State of Charge & Cycling</span>
        </CardTitle>
        <CardDescription>
          Hourly battery energy stored (kWh) and active charge / discharge cycles.
        </CardDescription>
      </CardHeader>
      <CardContent>
        <div className="h-[280px] w-full">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={chartData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
              <XAxis dataKey="hour" stroke="#64748b" fontSize={11} tickLine={false} />
              <YAxis stroke="#64748b" fontSize={11} tickLine={false} />
              <Tooltip
                contentStyle={{
                  backgroundColor: "#0f172a",
                  borderColor: "#334155",
                  borderRadius: "8px",
                  fontSize: "12px",
                }}
              />
              <Legend wrapperStyle={{ fontSize: "12px", paddingTop: "10px" }} />
              <Line
                type="monotone"
                dataKey="soc"
                name="Battery Energy / SoC (kWh)"
                stroke="#10b981"
                strokeWidth={2.5}
                dot={false}
              />
              <Line
                type="step"
                dataKey="charge"
                name="Charge Power (kW)"
                stroke="#06b6d4"
                strokeWidth={1.5}
                dot={false}
              />
              <Line
                type="step"
                dataKey="discharge"
                name="Discharge Power (kW)"
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

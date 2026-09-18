"use client";

import React from "react";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/card";
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

interface SolarChartProps {
  schedule?: HourSchedule[];
}

export function SolarChart({ schedule }: SolarChartProps) {
  const chartData =
    schedule && schedule.length === 24
      ? schedule.map((item) => ({
          hour: `${String(item.hour).padStart(2, "0")}:00`,
          effective_solar: item.effective_solar_kwh,
          solar_used: item.solar_used_kwh,
        }))
      : Array.from({ length: 24 }, (_, i) => ({
          hour: `${String(i).padStart(2, "0")}:00`,
          effective_solar: i >= 6 && i <= 17 ? Math.sin((i - 6) / 11 * Math.PI) * 40 : 0,
          solar_used: i >= 6 && i <= 17 ? Math.sin((i - 6) / 11 * Math.PI) * 35 : 0,
        }));

  return (
    <Card className="border-slate-800 bg-slate-900/50">
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-base">
          <Sun className="h-5 w-5 text-amber-400" />
          <span>Solar Generation & Utilization</span>
        </CardTitle>
        <CardDescription>
          Hourly solar potential versus energy dispatched to campus loads.
        </CardDescription>
      </CardHeader>
      <CardContent>
        <div className="h-[280px] w-full">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={chartData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
              <defs>
                <linearGradient id="solarGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#f59e0b" stopOpacity={0.4} />
                  <stop offset="95%" stopColor="#f59e0b" stopOpacity={0} />
                </linearGradient>
                <linearGradient id="solarUsedGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#eab308" stopOpacity={0.6} />
                  <stop offset="95%" stopColor="#eab308" stopOpacity={0.1} />
                </linearGradient>
              </defs>
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
              <Area
                type="monotone"
                dataKey="effective_solar"
                name="Available Solar (kWh)"
                stroke="#f59e0b"
                fillOpacity={1}
                fill="url(#solarGrad)"
              />
              <Area
                type="monotone"
                dataKey="solar_used"
                name="Dispatched Solar (kWh)"
                stroke="#eab308"
                fillOpacity={1}
                fill="url(#solarUsedGrad)"
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </CardContent>
    </Card>
  );
}

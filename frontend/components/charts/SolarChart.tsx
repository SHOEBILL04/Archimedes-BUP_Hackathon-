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
          effective_solar: i >= 6 && i <= 17 ? Math.sin(((i - 6) / 11) * Math.PI) * 40 : 0,
          solar_used: i >= 6 && i <= 17 ? Math.sin(((i - 6) / 11) * Math.PI) * 35 : 0,
        }));

  return (
    <Card className="bento-card border-white/[0.08] hover:border-amber-400/30 h-full flex flex-col justify-between">
      <CardHeader className="p-6 pb-2">
        <div className="flex items-center justify-between">
          <div className="space-y-1">
            <CardTitle className="flex items-center gap-2 text-sm font-semibold text-white">
              <Sun className="h-4 w-4 text-amber-400" />
              <span>Solar Generation & Utilization</span>
            </CardTitle>
            <CardDescription className="text-xs text-slate-400">
              Photovoltaic baseline vs. real-time energy directed into campus loads.
            </CardDescription>
          </div>
        </div>
      </CardHeader>
      <CardContent className="p-6 pt-2 flex-1">
        <div className="h-[280px] w-full">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={chartData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
              <defs>
                <linearGradient id="bentoSolarGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#f59e0b" stopOpacity={0.3} />
                  <stop offset="95%" stopColor="#f59e0b" stopOpacity={0} />
                </linearGradient>
                <linearGradient id="bentoSolarUsedGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#00f0ff" stopOpacity={0.45} />
                  <stop offset="95%" stopColor="#00f0ff" stopOpacity={0.05} />
                </linearGradient>
              </defs>
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
              <Area
                type="monotone"
                dataKey="effective_solar"
                name="Potential Solar (kWh)"
                stroke="#f59e0b"
                strokeWidth={1.5}
                fillOpacity={1}
                fill="url(#bentoSolarGrad)"
              />
              <Area
                type="monotone"
                dataKey="solar_used"
                name="Dispatched Solar (kWh)"
                stroke="#00f0ff"
                strokeWidth={2}
                fillOpacity={1}
                fill="url(#bentoSolarUsedGrad)"
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </CardContent>
    </Card>
  );
}

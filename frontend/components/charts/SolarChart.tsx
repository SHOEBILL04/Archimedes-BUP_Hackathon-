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
    <Card className="bento-card border-[rgba(28,49,46,0.08)] h-full flex flex-col justify-between">
      <CardHeader className="p-6 pb-2">
        <div className="flex items-center justify-between">
          <div className="space-y-1">
            <CardTitle className="flex items-center gap-2 text-sm font-bold text-[#1C312E]">
              <Sun className="h-4 w-4 text-[#D97757]" />
              <span>Solar Generation & Utilization</span>
            </CardTitle>
            <CardDescription className="text-xs text-[#6E8480]">
              Photovoltaic baseline vs. real-time clean energy directed into campus loads.
            </CardDescription>
          </div>
        </div>
      </CardHeader>
      <CardContent className="p-6 pt-2 flex-1">
        <div className="h-[280px] w-full">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={chartData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
              <defs>
                <linearGradient id="copperSolarGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#D97757" stopOpacity={0.35} />
                  <stop offset="95%" stopColor="#D97757" stopOpacity={0.02} />
                </linearGradient>
                <linearGradient id="sageSolarUsedGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#4E8773" stopOpacity={0.5} />
                  <stop offset="95%" stopColor="#4E8773" stopOpacity={0.05} />
                </linearGradient>
              </defs>
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
              <Area
                type="monotone"
                dataKey="effective_solar"
                name="Potential Solar (kWh)"
                stroke="#D97757"
                strokeWidth={1.5}
                strokeDasharray="4 4"
                fillOpacity={1}
                fill="url(#copperSolarGrad)"
              />
              <Area
                type="monotone"
                dataKey="solar_used"
                name="Clean Solar Utilized (kWh)"
                stroke="#4E8773"
                strokeWidth={2.5}
                fillOpacity={1}
                fill="url(#sageSolarUsedGrad)"
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </CardContent>
    </Card>
  );
}

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
import { Activity } from "lucide-react";

interface DemandChartProps {
  schedule?: HourSchedule[];
}

export function DemandChart({ schedule }: DemandChartProps) {
  const chartData =
    schedule && schedule.length === 24
      ? schedule.map((item) => ({
          hour: `${String(item.hour).padStart(2, "0")}:00`,
          demand: item.demand_kwh,
          grid: item.grid_kwh,
        }))
      : Array.from({ length: 24 }, (_, i) => ({
          hour: `${String(i).padStart(2, "0")}:00`,
          demand: 35 + Math.sin(i / 3) * 15,
          grid: 25 + Math.sin(i / 3) * 10,
        }));

  return (
    <Card className="bento-card border-[rgba(28,49,46,0.08)] h-full flex flex-col justify-between">
      <CardHeader className="p-6 pb-2">
        <div className="flex items-center justify-between">
          <div className="space-y-1">
            <CardTitle className="flex items-center gap-2 text-sm font-bold text-[#1C312E]">
              <Activity className="h-4 w-4 text-[#4E8773]" />
              <span>Campus Demand vs. Grid Import</span>
            </CardTitle>
            <CardDescription className="text-xs text-[#6E8480]">
              Hourly comparison between gross campus energy demand and grid import.
            </CardDescription>
          </div>
          <span className="text-[10px] font-mono text-[#4E8773] bg-[#E8EFE9] border border-[#4E8773]/30 px-2 py-0.5 rounded-md hidden sm:inline-block font-bold">
            24h Profile
          </span>
        </div>
      </CardHeader>
      <CardContent className="p-6 pt-2 flex-1">
        <div className="h-[280px] w-full">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={chartData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
              <defs>
                <linearGradient id="slateDemandGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#1C312E" stopOpacity={0.25} />
                  <stop offset="95%" stopColor="#1C312E" stopOpacity={0.02} />
                </linearGradient>
                <linearGradient id="sageGridGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#4E8773" stopOpacity={0.45} />
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
                dataKey="demand"
                name="Gross Demand (kWh)"
                stroke="#1C312E"
                strokeWidth={2}
                fillOpacity={1}
                fill="url(#slateDemandGrad)"
              />
              <Area
                type="monotone"
                dataKey="grid"
                name="Grid Import (kWh)"
                stroke="#4E8773"
                strokeWidth={2.5}
                fillOpacity={1}
                fill="url(#sageGridGrad)"
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </CardContent>
    </Card>
  );
}

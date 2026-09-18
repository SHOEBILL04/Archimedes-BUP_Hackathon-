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
    <Card className="bento-card border-slate-200/90 hover:border-slate-300 h-full flex flex-col justify-between">
      <CardHeader className="p-6 pb-2">
        <div className="flex items-center justify-between">
          <div className="space-y-1">
            <CardTitle className="flex items-center gap-2 text-sm font-bold text-[#0F172A]">
              <Activity className="h-4 w-4 text-sky-600" />
              <span>Campus Demand vs. Grid Import</span>
            </CardTitle>
            <CardDescription className="text-xs text-slate-500">
              Hourly comparison between gross campus energy demand and grid import.
            </CardDescription>
          </div>
          <span className="text-[10px] font-mono text-sky-700 bg-sky-50 border border-sky-200/80 px-2 py-0.5 rounded-md hidden sm:inline-block font-semibold">
            24h Profile
          </span>
        </div>
      </CardHeader>
      <CardContent className="p-6 pt-2 flex-1">
        <div className="h-[280px] w-full">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={chartData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
              <defs>
                <linearGradient id="cleanDemandGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#0F172A" stopOpacity={0.2} />
                  <stop offset="95%" stopColor="#0F172A" stopOpacity={0.02} />
                </linearGradient>
                <linearGradient id="cleanGridGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#0EA5E9" stopOpacity={0.35} />
                  <stop offset="95%" stopColor="#0EA5E9" stopOpacity={0.03} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#E2E8F0" />
              <XAxis dataKey="hour" stroke="#64748B" fontSize={10} tickLine={false} />
              <YAxis stroke="#64748B" fontSize={10} tickLine={false} />
              <Tooltip
                contentStyle={{
                  backgroundColor: "#FFFFFF",
                  borderColor: "#E2E8F0",
                  borderRadius: "12px",
                  fontSize: "11px",
                  fontFamily: "monospace",
                  color: "#0F172A",
                  boxShadow: "0 10px 25px -4px rgba(15, 23, 42, 0.08)",
                }}
              />
              <Legend wrapperStyle={{ fontSize: "11px", fontFamily: "monospace", paddingTop: "8px" }} />
              <Area
                type="monotone"
                dataKey="demand"
                name="Gross Demand (kWh)"
                stroke="#0F172A"
                strokeWidth={2}
                fillOpacity={1}
                fill="url(#cleanDemandGrad)"
              />
              <Area
                type="monotone"
                dataKey="grid"
                name="Grid Import (kWh)"
                stroke="#0284C7"
                strokeWidth={2.5}
                fillOpacity={1}
                fill="url(#cleanGridGrad)"
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </CardContent>
    </Card>
  );
}

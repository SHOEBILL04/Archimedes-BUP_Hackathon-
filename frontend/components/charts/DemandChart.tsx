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
    <Card className="bento-card border-slate-200/90 hover:border-[#425B9A]/30 h-full flex flex-col justify-between">
      <CardHeader className="p-6 pb-2">
        <div className="flex items-center justify-between">
          <div className="space-y-1">
            <CardTitle className="flex items-center gap-2 text-sm font-bold text-[#425B9A]">
              <Activity className="h-4 w-4 text-[#425B9A]" />
              <span>Campus Demand vs. Grid Import</span>
            </CardTitle>
            <CardDescription className="text-xs text-slate-500">
              Hourly comparison between gross campus energy demand and grid import.
            </CardDescription>
          </div>
          <span className="text-[10px] font-mono text-[#425B9A] bg-[#425B9A]/10 border border-[#425B9A]/20 px-2 py-0.5 rounded-md hidden sm:inline-block font-bold">
            24h Profile
          </span>
        </div>
      </CardHeader>
      <CardContent className="p-6 pt-2 flex-1">
        <div className="h-[280px] w-full">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={chartData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
              <defs>
                <linearGradient id="lightDemandGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#76C0EC" stopOpacity={0.45} />
                  <stop offset="95%" stopColor="#76C0EC" stopOpacity={0.05} />
                </linearGradient>
                <linearGradient id="lightGridGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#425B9A" stopOpacity={0.35} />
                  <stop offset="95%" stopColor="#425B9A" stopOpacity={0.02} />
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
                  color: "#1E293B",
                  boxShadow: "0 10px 25px -4px rgba(66, 91, 154, 0.15)",
                }}
              />
              <Legend wrapperStyle={{ fontSize: "11px", fontFamily: "monospace", paddingTop: "8px" }} />
              <Area
                type="monotone"
                dataKey="demand"
                name="Gross Demand (kWh)"
                stroke="#76C0EC"
                strokeWidth={2}
                fillOpacity={1}
                fill="url(#lightDemandGrad)"
              />
              <Area
                type="monotone"
                dataKey="grid"
                name="Grid Dispatched (kWh)"
                stroke="#425B9A"
                strokeWidth={2.5}
                fillOpacity={1}
                fill="url(#lightGridGrad)"
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </CardContent>
    </Card>
  );
}

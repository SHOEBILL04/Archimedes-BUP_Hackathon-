import React from "react";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/card";
import { HourSchedule } from "@/types/energy";
import { formatCurrencyBDT, formatNumber } from "@/lib/utils";
import { CalendarClock, Download } from "lucide-react";
import { Button } from "@/components/ui/button";

interface ScheduleTableProps {
  schedule?: HourSchedule[];
}

export function ScheduleTable({ schedule }: ScheduleTableProps) {
  // Generate default 24-hour items if no response yet
  const rows: HourSchedule[] =
    schedule && schedule.length === 24
      ? schedule
      : Array.from({ length: 24 }, (_, i) => ({
          hour: i,
          demand_kwh: 40 + Math.sin(i / 3) * 15,
          effective_solar_kwh: i >= 6 && i <= 17 ? Math.sin(((i - 6) / 11) * Math.PI) * 35 : 0,
          solar_used_kwh: i >= 6 && i <= 17 ? Math.min(40, Math.sin(((i - 6) / 11) * Math.PI) * 35) : 0,
          battery_charge_kwh: 0,
          battery_discharge_kwh: 0,
          battery_energy_after_kwh: 40,
          grid_kwh: 35,
          tariff_bdt_per_kwh: 10,
          grid_cost_bdt: 350,
        }));

  return (
    <Card className="bento-card border-slate-200/90 hover:border-slate-300">
      <CardHeader className="p-6 pb-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div className="space-y-1">
            <CardTitle className="flex items-center gap-2 text-sm font-bold text-[#0F172A]">
              <CalendarClock className="h-4 w-4 text-slate-700" />
              <span>24-Hour Dispatch Matrix</span>
            </CardTitle>
            <CardDescription className="text-xs text-slate-500">
              Hourly chronological breakdown of solar consumption, battery charge/discharge cycles, and grid tariff costs.
            </CardDescription>
          </div>
          <Button
            variant="outline"
            size="sm"
            className="text-xs font-mono gap-1.5 h-8 w-fit text-slate-700 border-slate-200 hover:bg-slate-50"
            onClick={() => {
              const dataStr = "data:text/json;charset=utf-8," + encodeURIComponent(JSON.stringify(rows, null, 2));
              const downloadAnchor = document.createElement("a");
              downloadAnchor.setAttribute("href", dataStr);
              downloadAnchor.setAttribute("download", "dispatch_schedule_24h.json");
              document.body.appendChild(downloadAnchor);
              downloadAnchor.click();
              downloadAnchor.remove();
            }}
          >
            <Download className="h-3.5 w-3.5 text-slate-600" />
            <span>Export JSON</span>
          </Button>
        </div>
      </CardHeader>

      <CardContent className="p-6 pt-0">
        <div className="overflow-x-auto rounded-xl border border-slate-200 bg-white">
          <table className="w-full text-left text-xs border-collapse font-mono">
            <thead>
              <tr className="bg-slate-50/80 border-b border-slate-200 text-slate-600 text-[11px]">
                <th className="py-3 px-3.5 font-bold text-[#0F172A]">Hour</th>
                <th className="py-3 px-3.5 font-bold">Demand (kWh)</th>
                <th className="py-3 px-3.5 font-bold text-amber-700">Solar (kWh)</th>
                <th className="py-3 px-3.5 font-bold text-emerald-700">Charge</th>
                <th className="py-3 px-3.5 font-bold text-rose-600">Discharge</th>
                <th className="py-3 px-3.5 font-bold text-indigo-700">SoC (kWh)</th>
                <th className="py-3 px-3.5 font-bold text-sky-700">Grid (kWh)</th>
                <th className="py-3 px-3.5 font-bold text-slate-500">Tariff (BDT)</th>
                <th className="py-3 px-3.5 font-bold text-right text-[#0F172A]">Cost (BDT)</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 text-slate-700 text-[11px]">
              {rows.map((row) => (
                <tr
                  key={row.hour}
                  className="hover:bg-slate-50/70 transition-colors group"
                >
                  <td className="py-2.5 px-3.5 font-bold text-[#0F172A]">
                    {String(row.hour).padStart(2, "0")}:00
                  </td>
                  <td className="py-2.5 px-3.5">{formatNumber(row.demand_kwh, 1)}</td>
                  <td className="py-2.5 px-3.5 text-amber-700 font-medium">
                    {formatNumber(row.solar_used_kwh, 1)}
                  </td>
                  <td className="py-2.5 px-3.5 text-emerald-700 font-medium">
                    {row.battery_charge_kwh > 0 ? `+${formatNumber(row.battery_charge_kwh, 1)}` : "—"}
                  </td>
                  <td className="py-2.5 px-3.5 text-rose-600 font-medium">
                    {row.battery_discharge_kwh > 0 ? `-${formatNumber(row.battery_discharge_kwh, 1)}` : "—"}
                  </td>
                  <td className="py-2.5 px-3.5 text-indigo-700 font-semibold">
                    {formatNumber(row.battery_energy_after_kwh, 1)}
                  </td>
                  <td className="py-2.5 px-3.5 font-medium text-sky-700">
                    {formatNumber(row.grid_kwh, 1)}
                  </td>
                  <td className="py-2.5 px-3.5 text-slate-500">
                    {formatNumber(row.tariff_bdt_per_kwh, 1)}
                  </td>
                  <td className="py-2.5 px-3.5 font-bold text-[#0F172A] text-right">
                    {formatCurrencyBDT(row.grid_cost_bdt)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </CardContent>
    </Card>
  );
}

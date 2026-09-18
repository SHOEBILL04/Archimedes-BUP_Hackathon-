import React from "react";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/card";
import { HourSchedule } from "@/types/energy";
import { formatCurrencyBDT, formatNumber } from "@/lib/utils";
import { CalendarClock } from "lucide-react";

interface ScheduleTableProps {
  schedule?: HourSchedule[];
}

export function ScheduleTable({ schedule }: ScheduleTableProps) {
  // Generate dummy 24-hour items if no response yet
  const rows: HourSchedule[] =
    schedule && schedule.length === 24
      ? schedule
      : Array.from({ length: 24 }, (_, i) => ({
          hour: i,
          demand_kwh: 40 + Math.sin(i / 3) * 15,
          effective_solar_kwh: i >= 6 && i <= 17 ? Math.sin((i - 6) / 11 * Math.PI) * 35 : 0,
          solar_used_kwh: i >= 6 && i <= 17 ? Math.min(40, Math.sin((i - 6) / 11 * Math.PI) * 35) : 0,
          battery_charge_kwh: 0,
          battery_discharge_kwh: 0,
          battery_energy_after_kwh: 40,
          grid_kwh: 35,
          tariff_bdt_per_kwh: 10,
          grid_cost_bdt: 350,
        }));

  return (
    <Card className="border-slate-800 bg-slate-900/50">
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-base">
          <CalendarClock className="h-5 w-5 text-emerald-400" />
          <span>24-Hour Dispatch Schedule</span>
        </CardTitle>
        <CardDescription>
          Hourly breakdown of generation, battery state of charge (SoC), grid import, and cost in BDT.
        </CardDescription>
      </CardHeader>

      <CardContent>
        <div className="overflow-x-auto rounded-lg border border-slate-800/80">
          <table className="w-full text-left text-xs border-collapse">
            <thead>
              <tr className="bg-slate-950/80 border-b border-slate-800 text-slate-400">
                <th className="py-3 px-3.5 font-semibold">Hour</th>
                <th className="py-3 px-3.5 font-semibold">Demand (kWh)</th>
                <th className="py-3 px-3.5 font-semibold">Solar Used (kWh)</th>
                <th className="py-3 px-3.5 font-semibold">Battery Charge</th>
                <th className="py-3 px-3.5 font-semibold">Battery Discharge</th>
                <th className="py-3 px-3.5 font-semibold">Battery SoC (kWh)</th>
                <th className="py-3 px-3.5 font-semibold">Grid Import (kWh)</th>
                <th className="py-3 px-3.5 font-semibold">Tariff (BDT)</th>
                <th className="py-3 px-3.5 font-semibold text-right">Cost (BDT)</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60 text-slate-300">
              {rows.map((row) => (
                <tr
                  key={row.hour}
                  className="hover:bg-slate-800/30 transition-colors"
                >
                  <td className="py-2.5 px-3.5 font-medium text-slate-200">
                    {String(row.hour).padStart(2, "0")}:00
                  </td>
                  <td className="py-2.5 px-3.5">{formatNumber(row.demand_kwh, 1)}</td>
                  <td className="py-2.5 px-3.5 text-amber-300 font-medium">
                    {formatNumber(row.solar_used_kwh, 1)}
                  </td>
                  <td className="py-2.5 px-3.5 text-teal-300">
                    {row.battery_charge_kwh > 0 ? `+${formatNumber(row.battery_charge_kwh, 1)}` : "0.0"}
                  </td>
                  <td className="py-2.5 px-3.5 text-rose-300">
                    {row.battery_discharge_kwh > 0 ? `-${formatNumber(row.battery_discharge_kwh, 1)}` : "0.0"}
                  </td>
                  <td className="py-2.5 px-3.5 font-medium text-emerald-400">
                    {formatNumber(row.battery_energy_after_kwh, 1)}
                  </td>
                  <td className="py-2.5 px-3.5 font-semibold text-slate-200">
                    {formatNumber(row.grid_kwh, 1)}
                  </td>
                  <td className="py-2.5 px-3.5 text-slate-400">
                    {formatNumber(row.tariff_bdt_per_kwh, 1)}
                  </td>
                  <td className="py-2.5 px-3.5 font-bold text-slate-100 text-right">
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

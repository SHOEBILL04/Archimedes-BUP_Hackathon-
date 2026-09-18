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
    <Card className="bento-card border-[rgba(28,49,46,0.08)]">
      <CardHeader className="p-6 pb-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div className="space-y-1">
            <CardTitle className="flex items-center gap-2 text-sm font-bold text-[#1C312E]">
              <CalendarClock className="h-4 w-4 text-[#4E8773]" />
              <span>24-Hour Dispatch Matrix</span>
            </CardTitle>
            <CardDescription className="text-xs text-[#6E8480]">
              Hourly chronological breakdown of solar consumption, battery charge/discharge cycles, and grid tariff costs.
            </CardDescription>
          </div>
          <Button
            variant="outline"
            size="sm"
            className="text-xs font-mono gap-1.5 h-8 w-fit text-[#1C312E] border-[rgba(28,49,46,0.12)] hover:bg-[#F4F7F4]"
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
            <Download className="h-3.5 w-3.5 text-[#4E8773]" />
            <span>Export JSON</span>
          </Button>
        </div>
      </CardHeader>

      <CardContent className="p-6 pt-0">
        <div className="overflow-x-auto rounded-xl border border-[rgba(28,49,46,0.08)] bg-white">
          <table className="w-full text-left text-xs border-collapse font-mono">
            <thead>
              <tr className="bg-[#E8EFE9] border-b border-[rgba(28,49,46,0.1)] text-[#1C312E] text-[11px]">
                <th className="py-3 px-3.5 font-bold text-[#1C312E]">Hour</th>
                <th className="py-3 px-3.5 font-bold">Demand (kWh)</th>
                <th className="py-3 px-3.5 font-bold text-[#4E8773]">Solar (kWh)</th>
                <th className="py-3 px-3.5 font-bold text-[#4E8773]">Charge</th>
                <th className="py-3 px-3.5 font-bold text-[#D97757]">Discharge</th>
                <th className="py-3 px-3.5 font-bold text-[#1C312E]">SoC (kWh)</th>
                <th className="py-3 px-3.5 font-bold text-[#1C312E]">Grid (kWh)</th>
                <th className="py-3 px-3.5 font-bold text-[#6E8480]">Tariff (BDT)</th>
                <th className="py-3 px-3.5 font-bold text-right text-[#1C312E]">Cost (BDT)</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[rgba(28,49,46,0.06)] text-[#1C312E] text-[11px]">
              {rows.map((row) => (
                <tr
                  key={row.hour}
                  className="hover:bg-[#F4F7F4] transition-colors group"
                >
                  <td className="py-2.5 px-3.5 font-bold text-[#1C312E]">
                    {String(row.hour).padStart(2, "0")}:00
                  </td>
                  <td className="py-2.5 px-3.5">{formatNumber(row.demand_kwh, 1)}</td>
                  <td className="py-2.5 px-3.5 text-[#4E8773] font-medium">
                    {formatNumber(row.solar_used_kwh, 1)}
                  </td>
                  <td className="py-2.5 px-3.5 text-[#4E8773] font-medium">
                    {row.battery_charge_kwh > 0 ? `+${formatNumber(row.battery_charge_kwh, 1)}` : "—"}
                  </td>
                  <td className="py-2.5 px-3.5 text-[#D97757] font-medium">
                    {row.battery_discharge_kwh > 0 ? `-${formatNumber(row.battery_discharge_kwh, 1)}` : "—"}
                  </td>
                  <td className="py-2.5 px-3.5 text-[#1C312E] font-bold">
                    {formatNumber(row.battery_energy_after_kwh, 1)}
                  </td>
                  <td className="py-2.5 px-3.5 font-medium text-[#1C312E]">
                    {formatNumber(row.grid_kwh, 1)}
                  </td>
                  <td className="py-2.5 px-3.5 text-[#6E8480]">
                    {formatNumber(row.tariff_bdt_per_kwh, 1)}
                  </td>
                  <td className="py-2.5 px-3.5 font-bold text-[#1C312E] text-right">
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

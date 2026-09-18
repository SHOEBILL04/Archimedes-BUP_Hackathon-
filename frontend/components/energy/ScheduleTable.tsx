"use client";

import React from "react";
import {
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
} from "@/components/ui/card";
import { HourSchedule } from "@/types/energy";
import { formatCurrencyBDT, formatNumber } from "@/lib/utils";
import { CalendarClock, Download } from "lucide-react";
import { Button } from "@/components/ui/button";
import { HOURS_IN_HORIZON } from "@/lib/constants";

interface ScheduleTableProps {
  schedule?: HourSchedule[];
}

/** Illustrative profile shown before the first optimization run. */
function placeholderSchedule(): HourSchedule[] {
  return Array.from({ length: HOURS_IN_HORIZON }, (_, i) => ({
    hour: i,
    demand_kwh: 40 + Math.sin(i / 3) * 15,
    effective_solar_kwh:
      i >= 6 && i <= 17 ? Math.sin(((i - 6) / 11) * Math.PI) * 35 : 0,
    solar_used_kwh:
      i >= 6 && i <= 17
        ? Math.min(40, Math.sin(((i - 6) / 11) * Math.PI) * 35)
        : 0,
    battery_charge_kwh: 0,
    battery_discharge_kwh: 0,
    battery_energy_after_kwh: 40,
    grid_kwh: 35,
    tariff_bdt_per_kwh: 10,
    grid_cost_bdt: 350,
  }));
}

export function ScheduleTable({ schedule }: ScheduleTableProps) {
  const rows =
    schedule && schedule.length === HOURS_IN_HORIZON
      ? schedule
      : placeholderSchedule();

  const handleExport = () => {
    const dataStr =
      "data:text/json;charset=utf-8," +
      encodeURIComponent(JSON.stringify(rows, null, 2));
    const anchor = document.createElement("a");
    anchor.setAttribute("href", dataStr);
    anchor.setAttribute("download", "dispatch_schedule_24h.json");
    document.body.appendChild(anchor);
    anchor.click();
    anchor.remove();
  };

  return (
    <Card static>
      <CardHeader className="p-6 pb-4">
        <div className="flex flex-col justify-between gap-3 sm:flex-row sm:items-center">
          <div className="space-y-1">
            <CardTitle className="flex items-center gap-2 text-sm">
              <CalendarClock className="h-4 w-4" />
              <span>24-Hour Dispatch Matrix</span>
            </CardTitle>
            <CardDescription>
              Hourly chronological breakdown of solar consumption, battery
              charge/discharge cycles, and grid tariff costs.
            </CardDescription>
          </div>
          <Button
            variant="outline"
            size="sm"
            className="h-8 w-fit gap-1.5 font-mono text-xs"
            onClick={handleExport}
          >
            <Download className="h-3.5 w-3.5" />
            <span>Export JSON</span>
          </Button>
        </div>
      </CardHeader>

      <CardContent className="p-6 pt-0">
        <div className="overflow-x-auto rounded-tile border border-line bg-surface">
          <table className="w-full border-collapse text-left font-mono text-xs">
            <caption className="sr-only">
              Hour-by-hour campus energy dispatch schedule
            </caption>
            <thead>
              <tr className="border-b border-line bg-canvas text-[11px] text-ink-muted">
                <th scope="col" className="px-3.5 py-3 font-bold text-brand">
                  Hour
                </th>
                <th scope="col" className="px-3.5 py-3 font-bold">
                  Demand (kWh)
                </th>
                <th scope="col" className="px-3.5 py-3 font-bold text-cream-ink">
                  Solar (kWh)
                </th>
                <th scope="col" className="px-3.5 py-3 font-bold text-accent-ink">
                  Charge
                </th>
                <th scope="col" className="px-3.5 py-3 font-bold text-coral-ink">
                  Discharge
                </th>
                <th scope="col" className="px-3.5 py-3 font-bold text-brand">
                  SoC (kWh)
                </th>
                <th scope="col" className="px-3.5 py-3 font-bold">
                  Grid (kWh)
                </th>
                <th scope="col" className="px-3.5 py-3 font-bold">
                  Tariff (BDT)
                </th>
                <th scope="col" className="px-3.5 py-3 text-right font-bold text-brand">
                  Cost (BDT)
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-line text-[11px] text-ink-muted">
              {rows.map((row) => (
                <tr
                  key={row.hour}
                  className="transition-colors hover:bg-brand-50"
                >
                  <th
                    scope="row"
                    className="px-3.5 py-2.5 text-left font-bold text-brand"
                  >
                    {String(row.hour).padStart(2, "0")}:00
                  </th>
                  <td className="px-3.5 py-2.5">
                    {formatNumber(row.demand_kwh, 1)}
                  </td>
                  <td className="px-3.5 py-2.5 font-medium text-cream-ink">
                    {formatNumber(row.solar_used_kwh, 1)}
                  </td>
                  <td className="px-3.5 py-2.5 text-accent-ink">
                    {row.battery_charge_kwh > 0
                      ? `+${formatNumber(row.battery_charge_kwh, 1)}`
                      : "—"}
                  </td>
                  <td className="px-3.5 py-2.5 text-coral-ink">
                    {row.battery_discharge_kwh > 0
                      ? `-${formatNumber(row.battery_discharge_kwh, 1)}`
                      : "—"}
                  </td>
                  <td className="px-3.5 py-2.5 font-bold text-brand">
                    {formatNumber(row.battery_energy_after_kwh, 1)}
                  </td>
                  <td className="px-3.5 py-2.5 font-medium text-ink">
                    {formatNumber(row.grid_kwh, 1)}
                  </td>
                  <td className="px-3.5 py-2.5">
                    {formatNumber(row.tariff_bdt_per_kwh, 1)}
                  </td>
                  <td className="bg-cream/50 px-3.5 py-2.5 text-right font-bold text-brand">
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

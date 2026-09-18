"use client";

import React, { useState } from "react";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { DEFAULT_SAMPLE_SCENARIO } from "@/lib/constants";
import { EnergyScenario, OptimizationResponse } from "@/types/energy";
import { apiClient } from "@/lib/api/client";
import { Sparkles, BatteryCharging, Send, Loader2 } from "lucide-react";

interface ScenarioFormProps {
  onOptimized?: (result: OptimizationResponse) => void;
}

export function ScenarioForm({ onOptimized }: ScenarioFormProps) {
  const [scenario, setScenario] = useState<EnergyScenario>(DEFAULT_SAMPLE_SCENARIO);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);

    try {
      const result = await apiClient.optimizeEnergy(scenario);
      if (onOptimized) {
        onOptimized(result);
      }
    } catch (err: unknown) {
      setError(
        err instanceof Error ? err.message : "Failed to run optimization request."
      );
    } finally {
      setLoading(false);
    }
  };

  return (
    <Card className="border-slate-800 bg-slate-900/50">
      <CardHeader>
        <div className="flex items-center justify-between">
          <div className="space-y-1">
            <CardTitle className="flex items-center gap-2 text-lg">
              <Sparkles className="h-5 w-5 text-emerald-400" />
              <span>Campus Scenario & Operator Notes</span>
            </CardTitle>
            <CardDescription>
              Configure 24-hour campus profile, battery parameters, and free-form operator directives.
            </CardDescription>
          </div>
          <div className="flex items-center gap-2 text-xs text-slate-400 bg-slate-800/80 px-3 py-1.5 rounded-lg border border-slate-700/60">
            <BatteryCharging className="h-4 w-4 text-emerald-400" />
            <span>Capacity: {scenario.battery.capacity_kwh} kWh</span>
          </div>
        </div>
      </CardHeader>

      <CardContent>
        <form onSubmit={handleSubmit} className="space-y-6">
          {/* Operator Notes Area */}
          <div className="space-y-2">
            <label className="text-xs font-semibold text-slate-300 uppercase tracking-wider">
              Natural Language Operator Directives (1-3 Notes)
            </label>
            <div className="space-y-2">
              {scenario.operator_notes.map((note, idx) => (
                <input
                  key={idx}
                  type="text"
                  value={note}
                  onChange={(e) => {
                    const newNotes = [...scenario.operator_notes];
                    newNotes[idx] = e.target.value;
                    setScenario({ ...scenario, operator_notes: newNotes });
                  }}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3.5 py-2 text-sm text-slate-200 placeholder-slate-500 focus:outline-none focus:border-emerald-500 transition-colors"
                  placeholder={`Directive #${idx + 1}`}
                />
              ))}
            </div>
          </div>

          {/* Battery Quick Specs */}
          <div className="grid grid-cols-2 md:grid-cols-5 gap-3 pt-2">
            <div className="bg-slate-950/60 p-3 rounded-lg border border-slate-800/80">
              <span className="text-[11px] text-slate-400 block mb-1">Capacity</span>
              <span className="text-sm font-semibold text-slate-200">
                {scenario.battery.capacity_kwh} kWh
              </span>
            </div>
            <div className="bg-slate-950/60 p-3 rounded-lg border border-slate-800/80">
              <span className="text-[11px] text-slate-400 block mb-1">Initial Energy</span>
              <span className="text-sm font-semibold text-slate-200">
                {scenario.battery.initial_energy_kwh} kWh
              </span>
            </div>
            <div className="bg-slate-950/60 p-3 rounded-lg border border-slate-800/80">
              <span className="text-[11px] text-slate-400 block mb-1">Min Reserve</span>
              <span className="text-sm font-semibold text-slate-200">
                {scenario.battery.minimum_energy_kwh} kWh
              </span>
            </div>
            <div className="bg-slate-950/60 p-3 rounded-lg border border-slate-800/80">
              <span className="text-[11px] text-slate-400 block mb-1">Max Charge/hr</span>
              <span className="text-sm font-semibold text-slate-200">
                {scenario.battery.max_charge_kwh_per_hour} kW
              </span>
            </div>
            <div className="bg-slate-950/60 p-3 rounded-lg border border-slate-800/80">
              <span className="text-[11px] text-slate-400 block mb-1">Max Discharge/hr</span>
              <span className="text-sm font-semibold text-slate-200">
                {scenario.battery.max_discharge_kwh_per_hour} kW
              </span>
            </div>
          </div>

          {error && (
            <div className="p-3 text-xs bg-rose-950/40 border border-rose-800/80 text-rose-300 rounded-lg">
              {error}
            </div>
          )}

          <div className="flex justify-end pt-2">
            <Button
              type="submit"
              disabled={loading}
              className="gap-2 px-5 py-2.5 font-semibold text-sm"
            >
              {loading ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" />
                  <span>Optimizing Dispatch...</span>
                </>
              ) : (
                <>
                  <Send className="h-4 w-4" />
                  <span>Execute Optimization Pipeline</span>
                </>
              )}
            </Button>
          </div>
        </form>
      </CardContent>
    </Card>
  );
}

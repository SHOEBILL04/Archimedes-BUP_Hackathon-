"use client";

import React, { useState } from "react";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { DEFAULT_SAMPLE_SCENARIO } from "@/lib/constants";
import { EnergyScenario, OptimizationResponse } from "@/types/energy";
import { apiClient } from "@/lib/api/client";
import { BatteryCharging, Send, Loader2, MessageSquareCode, SlidersHorizontal } from "lucide-react";

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
    <Card className="bento-card border-slate-200/90 hover:border-slate-300">
      <CardHeader className="p-6 pb-4">
        <div className="flex items-center justify-between">
          <div className="space-y-1">
            <CardTitle className="flex items-center gap-2 text-sm font-bold text-[#0F172A]">
              <MessageSquareCode className="h-4 w-4 text-emerald-600" />
              <span>Scenario & Directives Console</span>
            </CardTitle>
            <CardDescription className="text-xs text-slate-500">
              Configure 24-hr campus profile, battery bounds, and natural-language operator directives.
            </CardDescription>
          </div>
          <Badge variant="cyan" className="font-mono text-[10px] hidden sm:inline-flex">
            <SlidersHorizontal className="h-3 w-3 mr-1" />
            24h Profile
          </Badge>
        </div>
      </CardHeader>

      <CardContent className="p-6 pt-2">
        <form onSubmit={handleSubmit} className="space-y-5">
          {/* Operator Directives */}
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <label className="text-[11px] font-mono font-bold text-slate-600 uppercase tracking-wider">
                Operator Directives (1-3 Notes)
              </label>
              <span className="text-[10px] font-mono text-emerald-700 font-semibold">LLM Parser Target</span>
            </div>
            <div className="space-y-2">
              {scenario.operator_notes.map((note, idx) => (
                <div key={idx} className="relative group">
                  <span className="absolute left-3 top-2.5 font-mono text-[11px] font-bold text-emerald-600 select-none">
                    #{idx + 1}
                  </span>
                  <input
                    type="text"
                    value={note}
                    onChange={(e) => {
                      const newNotes = [...scenario.operator_notes];
                      newNotes[idx] = e.target.value;
                      setScenario({ ...scenario, operator_notes: newNotes });
                    }}
                    className="w-full bg-slate-50/70 border border-slate-200 rounded-xl pl-9 pr-3.5 py-2 text-xs text-slate-800 placeholder-slate-400 focus:outline-none focus:border-emerald-500 focus:ring-2 focus:ring-emerald-500/15 transition-all font-sans"
                    placeholder={`Operator Note #${idx + 1}`}
                  />
                </div>
              ))}
            </div>
          </div>

          {/* Battery Parameter Chips */}
          <div className="space-y-2">
            <div className="flex items-center gap-1.5 text-[11px] font-mono font-bold text-slate-600 uppercase tracking-wider">
              <BatteryCharging className="h-3.5 w-3.5 text-slate-700" />
              <span>Storage Constraints</span>
            </div>
            <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-2">
              <div className="bg-slate-50/80 p-2.5 rounded-xl border border-slate-200/80">
                <span className="text-[10px] font-mono text-slate-500 block mb-0.5">Capacity</span>
                <span className="text-xs font-mono font-bold text-[#0F172A]">
                  {scenario.battery.capacity_kwh} <span className="text-[10px] font-normal text-slate-500">kWh</span>
                </span>
              </div>
              <div className="bg-slate-50/80 p-2.5 rounded-xl border border-slate-200/80">
                <span className="text-[10px] font-mono text-slate-500 block mb-0.5">Initial SoC</span>
                <span className="text-xs font-mono font-bold text-[#0F172A]">
                  {scenario.battery.initial_energy_kwh} <span className="text-[10px] font-normal text-slate-500">kWh</span>
                </span>
              </div>
              <div className="bg-slate-50/80 p-2.5 rounded-xl border border-slate-200/80">
                <span className="text-[10px] font-mono text-slate-500 block mb-0.5">Reserve</span>
                <span className="text-xs font-mono font-bold text-[#0F172A]">
                  {scenario.battery.minimum_energy_kwh} <span className="text-[10px] font-normal text-slate-500">kWh</span>
                </span>
              </div>
              <div className="bg-slate-50/80 p-2.5 rounded-xl border border-slate-200/80">
                <span className="text-[10px] font-mono text-slate-500 block mb-0.5">Max Charge</span>
                <span className="text-xs font-mono font-bold text-[#0F172A]">
                  {scenario.battery.max_charge_kwh_per_hour} <span className="text-[10px] font-normal text-slate-500">kW</span>
                </span>
              </div>
              <div className="bg-slate-50/80 p-2.5 rounded-xl border border-slate-200/80">
                <span className="text-[10px] font-mono text-slate-500 block mb-0.5">Max Discharge</span>
                <span className="text-xs font-mono font-bold text-[#0F172A]">
                  {scenario.battery.max_discharge_kwh_per_hour} <span className="text-[10px] font-normal text-slate-500">kW</span>
                </span>
              </div>
            </div>
          </div>

          {error && (
            <div className="p-3 text-xs bg-rose-50 border border-rose-200 text-rose-700 rounded-xl font-mono">
              {error}
            </div>
          )}

          <div className="pt-1 flex items-center justify-between">
            <span className="text-[11px] font-mono text-slate-500">
              Deterministic Guardrails Active
            </span>
            <Button
              type="submit"
              disabled={loading}
              variant="emerald"
              className="gap-2 px-6 py-2.5 text-xs font-bold"
            >
              {loading ? (
                <>
                  <Loader2 className="h-3.5 w-3.5 animate-spin" />
                  <span>Solving LP Model...</span>
                </>
              ) : (
                <>
                  <Send className="h-3.5 w-3.5" />
                  <span>Run Optimization</span>
                </>
              )}
            </Button>
          </div>
        </form>
      </CardContent>
    </Card>
  );
}

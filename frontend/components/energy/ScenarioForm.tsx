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
    <Card className="bento-card border-white/[0.08] hover:border-cyan-400/30">
      <CardHeader className="p-6 pb-4">
        <div className="flex items-center justify-between">
          <div className="space-y-1">
            <CardTitle className="flex items-center gap-2 text-sm font-semibold text-white">
              <MessageSquareCode className="h-4 w-4 text-cyan-400" />
              <span>Scenario & Directives Console</span>
            </CardTitle>
            <CardDescription className="text-xs text-slate-400">
              Set 24-hr campus profile, battery bounds, and natural-language operator directives.
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
              <label className="text-[11px] font-mono text-slate-400 uppercase tracking-wider">
                Operator Directives (1-3 Notes)
              </label>
              <span className="text-[10px] font-mono text-cyan-400/80">LLM Parser Target</span>
            </div>
            <div className="space-y-2">
              {scenario.operator_notes.map((note, idx) => (
                <div key={idx} className="relative group">
                  <span className="absolute left-3 top-2.5 font-mono text-[11px] text-cyan-500/70 select-none">
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
                    className="w-full bg-[#060a14]/80 border border-white/[0.08] rounded-xl pl-9 pr-3.5 py-2 text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-cyan-400 focus:ring-1 focus:ring-cyan-400/50 transition-all font-sans"
                    placeholder={`Operator Note #${idx + 1}`}
                  />
                </div>
              ))}
            </div>
          </div>

          {/* Battery Parameter Chips */}
          <div className="space-y-2">
            <div className="flex items-center gap-1.5 text-[11px] font-mono text-slate-400 uppercase tracking-wider">
              <BatteryCharging className="h-3.5 w-3.5 text-cyan-400" />
              <span>Storage Constraints</span>
            </div>
            <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-2">
              <div className="bg-[#060a14]/70 p-2.5 rounded-xl border border-white/[0.06]">
                <span className="text-[10px] font-mono text-slate-400 block mb-0.5">Capacity</span>
                <span className="text-xs font-mono font-semibold text-white">
                  {scenario.battery.capacity_kwh} <span className="text-[10px] font-normal text-slate-400">kWh</span>
                </span>
              </div>
              <div className="bg-[#060a14]/70 p-2.5 rounded-xl border border-white/[0.06]">
                <span className="text-[10px] font-mono text-slate-400 block mb-0.5">Initial SoC</span>
                <span className="text-xs font-mono font-semibold text-white">
                  {scenario.battery.initial_energy_kwh} <span className="text-[10px] font-normal text-slate-400">kWh</span>
                </span>
              </div>
              <div className="bg-[#060a14]/70 p-2.5 rounded-xl border border-white/[0.06]">
                <span className="text-[10px] font-mono text-slate-400 block mb-0.5">Reserve</span>
                <span className="text-xs font-mono font-semibold text-white">
                  {scenario.battery.minimum_energy_kwh} <span className="text-[10px] font-normal text-slate-400">kWh</span>
                </span>
              </div>
              <div className="bg-[#060a14]/70 p-2.5 rounded-xl border border-white/[0.06]">
                <span className="text-[10px] font-mono text-slate-400 block mb-0.5">Max Charge</span>
                <span className="text-xs font-mono font-semibold text-white">
                  {scenario.battery.max_charge_kwh_per_hour} <span className="text-[10px] font-normal text-slate-400">kW</span>
                </span>
              </div>
              <div className="bg-[#060a14]/70 p-2.5 rounded-xl border border-white/[0.06]">
                <span className="text-[10px] font-mono text-slate-400 block mb-0.5">Max Discharge</span>
                <span className="text-xs font-mono font-semibold text-white">
                  {scenario.battery.max_discharge_kwh_per_hour} <span className="text-[10px] font-normal text-slate-400">kW</span>
                </span>
              </div>
            </div>
          </div>

          {error && (
            <div className="p-3 text-xs bg-rose-950/40 border border-rose-800/80 text-rose-300 rounded-xl font-mono">
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
              className="gap-2 px-6 py-2.5 text-xs font-semibold"
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

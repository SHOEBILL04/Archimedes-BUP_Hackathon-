"use client";

import React, { useState } from "react";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { DEFAULT_SAMPLE_SCENARIO } from "@/lib/constants";
import { OFFICIAL_SAMPLE_CASES } from "@/lib/sampleCases";
import { EnergyScenario, OptimizationResponse } from "@/types/energy";
import { apiClient } from "@/lib/api/client";
import {
  BatteryCharging,
  Send,
  Loader2,
  MessageSquareCode,
  SlidersHorizontal,
  Plus,
  Trash2,
  FolderOpen,
} from "lucide-react";

interface ScenarioFormProps {
  onOptimized?: (result: OptimizationResponse) => void;
  initialScenario?: EnergyScenario;
}

export function ScenarioForm({ onOptimized, initialScenario }: ScenarioFormProps) {
  const [scenario, setScenario] = useState<EnergyScenario>(
    initialScenario || DEFAULT_SAMPLE_SCENARIO
  );
  const [selectedCaseId, setSelectedCaseId] = useState<string>("custom");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSelectCase = (caseId: string) => {
    setSelectedCaseId(caseId);
    if (caseId === "custom") {
      setScenario(DEFAULT_SAMPLE_SCENARIO);
    } else {
      const found = OFFICIAL_SAMPLE_CASES.find((c) => c.id === caseId);
      if (found) {
        setScenario(JSON.parse(JSON.stringify(found.scenario)));
      }
    }
  };

  const handleBatteryChange = (
    key: keyof EnergyScenario["battery"],
    value: number
  ) => {
    setScenario((prev) => ({
      ...prev,
      battery: {
        ...prev.battery,
        [key]: isNaN(value) ? 0 : value,
      },
    }));
  };

  const handleNoteChange = (idx: number, text: string) => {
    setScenario((prev) => {
      const newNotes = [...prev.operator_notes];
      newNotes[idx] = text;
      return { ...prev, operator_notes: newNotes };
    });
  };

  const handleAddNote = () => {
    if (scenario.operator_notes.length >= 5) return;
    setScenario((prev) => ({
      ...prev,
      operator_notes: [...prev.operator_notes, ""],
    }));
  };

  const handleRemoveNote = (idx: number) => {
    setScenario((prev) => ({
      ...prev,
      operator_notes: prev.operator_notes.filter((_, i) => i !== idx),
    }));
  };

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
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
          <div className="space-y-1">
            <CardTitle className="flex items-center gap-2 text-sm font-bold text-[#0F172A]">
              <MessageSquareCode className="h-4 w-4 text-emerald-600" />
              <span>Scenario & Directives Console</span>
            </CardTitle>
            <CardDescription className="text-xs text-slate-500">
              Configure 24-hr campus profile, battery bounds, and natural-language operator directives.
            </CardDescription>
          </div>
          <Badge variant="cyan" className="font-mono text-[10px] w-fit">
            <SlidersHorizontal className="h-3 w-3 mr-1" />
            24h Profile
          </Badge>
        </div>

        {/* Case Preset Selector */}
        <div className="mt-4 pt-3 border-t border-slate-100 flex flex-col sm:flex-row sm:items-center gap-2">
          <label className="text-[11px] font-mono font-bold text-slate-600 flex items-center gap-1.5 shrink-0">
            <FolderOpen className="h-3.5 w-3.5 text-emerald-600" />
            <span>Preset Case:</span>
          </label>
          <select
            aria-label="Preset Case"
            value={selectedCaseId}
            onChange={(e) => handleSelectCase(e.target.value)}
            className="w-full bg-slate-50/90 border border-slate-200 rounded-xl px-3 py-1.5 text-xs text-slate-800 focus:outline-none focus:border-emerald-500 focus:ring-2 focus:ring-emerald-500/15 font-mono cursor-pointer"
          >
            <option value="custom">-- Custom Scenario (Default) --</option>
            {OFFICIAL_SAMPLE_CASES.map((c) => (
              <option key={c.id} value={c.id}>
                {c.label}
              </option>
            ))}
          </select>
        </div>
      </CardHeader>

      <CardContent className="p-6 pt-2">
        <form onSubmit={handleSubmit} className="space-y-5">
          {/* Operator Directives */}
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <label className="text-[11px] font-mono font-bold text-slate-600 uppercase tracking-wider">
                Operator Directives (Natural Language)
              </label>
              <button
                type="button"
                onClick={handleAddNote}
                disabled={scenario.operator_notes.length >= 5}
                className="text-[10px] font-mono text-emerald-700 hover:text-emerald-800 font-semibold flex items-center gap-1 disabled:opacity-40 transition-opacity"
              >
                <Plus className="h-3 w-3" />
                Add Directive
              </button>
            </div>
            <div className="space-y-2">
              {scenario.operator_notes.map((note, idx) => (
                <div key={idx} className="relative group flex items-center gap-1.5">
                  <div className="relative flex-1">
                    <span className="absolute left-3 top-2.5 font-mono text-[11px] font-bold text-emerald-600 select-none">
                      #{idx + 1}
                    </span>
                    <input
                      type="text"
                      value={note}
                      onChange={(e) => handleNoteChange(idx, e.target.value)}
                      className="w-full bg-slate-50/70 border border-slate-200 rounded-xl pl-9 pr-3.5 py-2 text-xs text-slate-800 placeholder-slate-400 focus:outline-none focus:border-emerald-500 focus:ring-2 focus:ring-emerald-500/15 transition-all font-sans"
                      placeholder={`Operator Note #${idx + 1} (e.g. "Do not charge battery from 6 PM to 8 PM")`}
                    />
                  </div>
                  {scenario.operator_notes.length > 1 && (
                    <button
                      type="button"
                      onClick={() => handleRemoveNote(idx)}
                      className="p-1.5 text-slate-400 hover:text-rose-600 transition-colors rounded-lg hover:bg-rose-50"
                      title="Remove note"
                    >
                      <Trash2 className="h-3.5 w-3.5" />
                    </button>
                  )}
                </div>
              ))}
            </div>
          </div>

          {/* Dynamic Battery Parameters */}
          <div className="space-y-2">
            <div className="flex items-center gap-1.5 text-[11px] font-mono font-bold text-slate-600 uppercase tracking-wider">
              <BatteryCharging className="h-3.5 w-3.5 text-slate-700" />
              <span>Storage Constraints (Editable)</span>
            </div>
            <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-2">
              <div className="bg-slate-50/80 p-2.5 rounded-xl border border-slate-200/80">
                <label className="text-[10px] font-mono text-slate-500 block mb-1">
                  Capacity (kWh)
                </label>
                <input
                  type="number"
                  min={1}
                  step={1}
                  value={scenario.battery.capacity_kwh}
                  onChange={(e) =>
                    handleBatteryChange("capacity_kwh", parseFloat(e.target.value))
                  }
                  className="w-full bg-white border border-slate-200 rounded-lg px-2 py-1 text-xs font-mono font-bold text-[#0F172A] focus:outline-none focus:border-emerald-500"
                />
              </div>

              <div className="bg-slate-50/80 p-2.5 rounded-xl border border-slate-200/80">
                <label className="text-[10px] font-mono text-slate-500 block mb-1">
                  Initial SoC (kWh)
                </label>
                <input
                  type="number"
                  min={0}
                  step={1}
                  value={scenario.battery.initial_energy_kwh}
                  onChange={(e) =>
                    handleBatteryChange("initial_energy_kwh", parseFloat(e.target.value))
                  }
                  className="w-full bg-white border border-slate-200 rounded-lg px-2 py-1 text-xs font-mono font-bold text-[#0F172A] focus:outline-none focus:border-emerald-500"
                />
              </div>

              <div className="bg-slate-50/80 p-2.5 rounded-xl border border-slate-200/80">
                <label className="text-[10px] font-mono text-slate-500 block mb-1">
                  Reserve (kWh)
                </label>
                <input
                  type="number"
                  min={0}
                  step={1}
                  value={scenario.battery.minimum_energy_kwh}
                  onChange={(e) =>
                    handleBatteryChange("minimum_energy_kwh", parseFloat(e.target.value))
                  }
                  className="w-full bg-white border border-slate-200 rounded-lg px-2 py-1 text-xs font-mono font-bold text-[#0F172A] focus:outline-none focus:border-emerald-500"
                />
              </div>

              <div className="bg-slate-50/80 p-2.5 rounded-xl border border-slate-200/80">
                <label className="text-[10px] font-mono text-slate-500 block mb-1">
                  Max Chg (kW)
                </label>
                <input
                  type="number"
                  min={0}
                  step={1}
                  value={scenario.battery.max_charge_kwh_per_hour}
                  onChange={(e) =>
                    handleBatteryChange(
                      "max_charge_kwh_per_hour",
                      parseFloat(e.target.value)
                    )
                  }
                  className="w-full bg-white border border-slate-200 rounded-lg px-2 py-1 text-xs font-mono font-bold text-[#0F172A] focus:outline-none focus:border-emerald-500"
                />
              </div>

              <div className="bg-slate-50/80 p-2.5 rounded-xl border border-slate-200/80">
                <label className="text-[10px] font-mono text-slate-500 block mb-1">
                  Max Dischg (kW)
                </label>
                <input
                  type="number"
                  min={0}
                  step={1}
                  value={scenario.battery.max_discharge_kwh_per_hour}
                  onChange={(e) =>
                    handleBatteryChange(
                      "max_discharge_kwh_per_hour",
                      parseFloat(e.target.value)
                    )
                  }
                  className="w-full bg-white border border-slate-200 rounded-lg px-2 py-1 text-xs font-mono font-bold text-[#0F172A] focus:outline-none focus:border-emerald-500"
                />
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

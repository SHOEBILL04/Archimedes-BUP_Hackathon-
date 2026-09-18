"use client";

import React, { useId, useState } from "react";
import {
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { DEFAULT_SAMPLE_SCENARIO } from "@/lib/constants";
import { EnergyScenario, OptimizationResponse } from "@/types/energy";
import { apiClient } from "@/lib/api/client";
import {
  BatteryCharging,
  Send,
  Loader2,
  MessageSquareCode,
  SlidersHorizontal,
} from "lucide-react";

interface ScenarioFormProps {
  onOptimized?: (result: OptimizationResponse) => void;
}

const STORAGE_FIELDS = [
  { key: "capacity_kwh", label: "Capacity", unit: "kWh" },
  { key: "initial_energy_kwh", label: "Initial SoC", unit: "kWh" },
  { key: "minimum_energy_kwh", label: "Reserve", unit: "kWh" },
  { key: "max_charge_kwh_per_hour", label: "Max Charge", unit: "kW" },
  { key: "max_discharge_kwh_per_hour", label: "Max Discharge", unit: "kW" },
] as const;

export function ScenarioForm({ onOptimized }: ScenarioFormProps) {
  const [scenario, setScenario] = useState<EnergyScenario>(
    DEFAULT_SAMPLE_SCENARIO
  );
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const fieldId = useId();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);

    try {
      const result = await apiClient.optimizeEnergy(scenario);
      onOptimized?.(result);
    } catch (err: unknown) {
      setError(
        err instanceof Error ? err.message : "Failed to run optimization request."
      );
    } finally {
      setLoading(false);
    }
  };

  return (
    <Card active={loading}>
      <CardHeader className="p-6 pb-4">
        <div className="flex items-center justify-between">
          <div className="space-y-1">
            <CardTitle className="flex items-center gap-2 text-sm">
              <MessageSquareCode className="h-4 w-4" />
              <span>Scenario &amp; Directives Console</span>
            </CardTitle>
            <CardDescription>
              Configure 24-hr campus profile, battery bounds, and
              natural-language operator directives.
            </CardDescription>
          </div>
          <Badge
            variant="accent"
            className="hidden font-mono text-[10px] sm:inline-flex"
          >
            <SlidersHorizontal className="mr-1 h-3 w-3" />
            24h Profile
          </Badge>
        </div>
      </CardHeader>

      <CardContent className="p-6 pt-2">
        <form onSubmit={handleSubmit} className="space-y-5">
          {/* Operator directives */}
          <fieldset className="space-y-2">
            <div className="flex items-center justify-between">
              <legend className="font-mono text-[11px] font-bold uppercase tracking-wider text-ink-muted">
                Operator Directives (1-3 Notes)
              </legend>
              <span className="font-mono text-[10px] text-brand">
                LLM Parser Target
              </span>
            </div>
            <div className="space-y-2">
              {scenario.operator_notes.map((note, idx) => (
                <div key={idx} className="relative">
                  <span
                    aria-hidden="true"
                    className="pointer-events-none absolute left-3 top-2.5 select-none font-mono text-[11px] font-bold text-brand"
                  >
                    #{idx + 1}
                  </span>
                  <input
                    id={`${fieldId}-note-${idx}`}
                    type="text"
                    value={note}
                    aria-label={`Operator note ${idx + 1}`}
                    onChange={(e) => {
                      const newNotes = [...scenario.operator_notes];
                      newNotes[idx] = e.target.value;
                      setScenario({ ...scenario, operator_notes: newNotes });
                    }}
                    className="w-full rounded-xl border border-line bg-canvas py-2 pl-9 pr-3.5 font-sans text-xs text-ink transition-all placeholder:text-ink-subtle focus:border-brand focus:outline-none focus:ring-2 focus:ring-brand/15"
                    placeholder={`Operator Note #${idx + 1}`}
                  />
                </div>
              ))}
            </div>
          </fieldset>

          {/* Battery bounds */}
          <div className="space-y-2">
            <div className="flex items-center gap-1.5 font-mono text-[11px] font-bold uppercase tracking-wider text-ink-muted">
              <BatteryCharging className="h-3.5 w-3.5 text-brand" />
              <span>Storage Constraints</span>
            </div>
            <dl className="grid grid-cols-2 gap-2 sm:grid-cols-3 lg:grid-cols-5">
              {STORAGE_FIELDS.map((field) => (
                <div
                  key={field.key}
                  className="rounded-xl border border-line bg-canvas p-2.5 transition-colors hover:border-brand/25"
                >
                  <dt className="mb-0.5 block font-mono text-[10px] text-ink-muted">
                    {field.label}
                  </dt>
                  <dd className="font-mono text-xs font-bold text-brand">
                    {scenario.battery[field.key]}{" "}
                    <span className="text-[10px] font-normal text-ink-muted">
                      {field.unit}
                    </span>
                  </dd>
                </div>
              ))}
            </dl>
          </div>

          {error && (
            <div
              role="alert"
              className="rounded-xl border border-coral/50 bg-coral-50 p-3 font-mono text-xs text-coral-ink"
            >
              {error}
            </div>
          )}

          <div className="flex items-center justify-between pt-1">
            <span className="font-mono text-[11px] text-ink-muted">
              Deterministic Guardrails Active
            </span>
            <Button
              type="submit"
              disabled={loading}
              variant="brand"
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

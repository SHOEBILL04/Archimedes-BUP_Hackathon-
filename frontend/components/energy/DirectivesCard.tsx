import React from "react";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { DirectiveInterpretation } from "@/types/energy";
import { Brain, Sparkles, CheckCircle2, XCircle, Clock } from "lucide-react";

interface DirectivesCardProps {
  directives?: DirectiveInterpretation[];
  statusMessage?: string;
}

export function DirectivesCard({ directives, statusMessage }: DirectivesCardProps) {
  if (!directives || directives.length === 0) {
    return (
      <Card className="bento-card border-slate-200/90">
        <CardHeader className="p-5 pb-3">
          <CardTitle className="flex items-center gap-2 text-sm font-bold text-[#425B9A]">
            <Brain className="h-4 w-4 text-[#425B9A]" />
            <span>AI Directive Interpretation (Groq LPU)</span>
          </CardTitle>
        </CardHeader>
        <CardContent className="p-5 pt-0 text-xs text-slate-500 font-mono">
          Enter operator notes and run optimization to see the Groq LLM parsed directives and LangSmith trace in real-time.
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className="bento-card border-slate-200/90 hover:border-[#425B9A]/30">
      <CardHeader className="p-5 pb-3 flex flex-row items-center justify-between">
        <CardTitle className="flex items-center gap-2 text-sm font-bold text-[#425B9A]">
          <Brain className="h-4 w-4 text-[#425B9A]" />
          <span>AI Directive Interpretation (Groq LPU)</span>
        </CardTitle>
        <Badge variant="indigo" className="font-mono text-[10px] gap-1">
          <Sparkles className="h-3 w-3" />
          <span>LangSmith Traced</span>
        </Badge>
      </CardHeader>

      <CardContent className="p-5 pt-0 space-y-3">
        {statusMessage && (
          <p className="text-[11px] font-mono text-emerald-700 bg-emerald-50 border border-emerald-200 p-2 rounded-lg">
            ✓ {statusMessage}
          </p>
        )}

        <div className="space-y-2">
          {directives.map((dir, idx) => {
            const adj = dir.structured_adjustment as Record<string, unknown> | null;
            const hours = (adj?.hours as number[]) || [];

            return (
              <div
                key={idx}
                className="p-3 rounded-xl border border-slate-200 bg-[#F8FAFC] flex flex-col sm:flex-row sm:items-center justify-between gap-2"
              >
                <div className="space-y-1">
                  <div className="flex items-center gap-2">
                    <span className="font-mono text-[11px] font-bold text-[#425B9A]">
                      Note #{dir.note_index + 1}
                    </span>
                    <Badge
                      variant={dir.applies ? "indigo" : "slate"}
                      className="font-mono text-[11px]"
                    >
                      {dir.directive_type}
                    </Badge>
                    {dir.applies ? (
                      <span className="inline-flex items-center gap-1 text-[11px] font-mono text-emerald-600 font-semibold">
                        <CheckCircle2 className="h-3.5 w-3.5" />
                        Applied to LP
                      </span>
                    ) : (
                      <span className="inline-flex items-center gap-1 text-[11px] font-mono text-slate-500">
                        <XCircle className="h-3.5 w-3.5" />
                        Ignored (no_op)
                      </span>
                    )}
                  </div>

                  {hours.length > 0 && (
                    <div className="flex items-center gap-1.5 text-[11px] font-mono text-slate-600">
                      <Clock className="h-3 w-3 text-slate-400" />
                      <span>Affected Hours: [{hours.join(", ")}]</span>
                    </div>
                  )}
                </div>

                <div className="text-right">
                  {dir.directive_type === "solar_reduction" && adj?.factor !== undefined && (
                    <span className="text-xs font-mono font-bold text-amber-700 bg-amber-50 border border-amber-200 px-2 py-1 rounded-md">
                      Usable Solar: {((Number(adj.factor)) * 100).toFixed(0)}%
                    </span>
                  )}
                  {dir.directive_type === "minimum_battery_reserve" && adj?.minimum_energy_kwh !== undefined && (
                    <span className="text-xs font-mono font-bold text-sky-700 bg-sky-50 border border-sky-200 px-2 py-1 rounded-md">
                      Reserve: {Number(adj.minimum_energy_kwh)} kWh
                    </span>
                  )}
                  {dir.directive_type === "max_grid_window" && adj?.max_grid_kwh !== undefined && (
                    <span className="text-xs font-mono font-bold text-rose-700 bg-rose-50 border border-rose-200 px-2 py-1 rounded-md">
                      Max Grid: {Number(adj.max_grid_kwh)} kWh
                    </span>
                  )}
                  {dir.directive_type === "no_charge_window" && (
                    <span className="text-xs font-mono font-bold text-indigo-700 bg-indigo-50 border border-indigo-200 px-2 py-1 rounded-md">
                      Charging Prohibited
                    </span>
                  )}
                  {dir.directive_type === "no_discharge_window" && (
                    <span className="text-xs font-mono font-bold text-indigo-700 bg-indigo-50 border border-indigo-200 px-2 py-1 rounded-md">
                      Discharging Prohibited
                    </span>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      </CardContent>
    </Card>
  );
}

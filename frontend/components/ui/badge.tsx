import * as React from "react";
import { cn } from "@/lib/utils";

export interface BadgeProps extends React.HTMLAttributes<HTMLDivElement> {
  variant?:
    | "default"
    | "emerald"
    | "cyan"
    | "amber"
    | "indigo"
    | "coral"
    | "slate"
    | "hero"
    | "hero-cyan"
    | "sky"
    | "cream"
    | "success"
    | "warning"
    | "secondary"
    | "outline";
}

function Badge({
  className,
  variant = "default",
  ...props
}: BadgeProps) {
  const variantStyles = {
    default: "bg-slate-100 text-slate-800 border-slate-200 font-semibold",
    emerald: "bg-emerald-50 text-emerald-700 border-emerald-200/80 font-semibold",
    cyan: "bg-sky-50 text-sky-700 border-sky-200/80 font-semibold",
    amber: "bg-amber-50 text-amber-800 border-amber-200/80 font-semibold",
    indigo: "bg-indigo-50 text-indigo-700 border-indigo-200/80 font-semibold",
    coral: "bg-rose-50 text-rose-700 border-rose-200/80 font-semibold",
    slate: "bg-slate-100 text-slate-700 border-slate-200 font-semibold",
    hero: "bg-emerald-400/15 text-emerald-300 border-emerald-400/30 font-semibold backdrop-blur-xs",
    "hero-cyan": "bg-sky-400/15 text-sky-300 border-sky-400/30 font-semibold backdrop-blur-xs",
    // Compatibility aliases
    sky: "bg-sky-50 text-sky-700 border-sky-200/80 font-semibold",
    cream: "bg-amber-50 text-amber-800 border-amber-200/80 font-semibold",
    success: "bg-emerald-50 text-emerald-700 border-emerald-200/80 font-semibold",
    warning: "bg-amber-50 text-amber-800 border-amber-200/80 font-semibold",
    secondary: "bg-slate-100 text-slate-700 border-slate-200",
    outline: "text-slate-600 border-slate-200 bg-white",
  };

  return (
    <div
      className={cn(
        "inline-flex items-center rounded-full border px-2.5 py-0.5 text-[11px] font-medium tracking-tight transition-colors",
        variantStyles[variant],
        className
      )}
      {...props}
    />
  );
}

export { Badge };

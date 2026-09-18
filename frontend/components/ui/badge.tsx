import * as React from "react";
import { cn } from "@/lib/utils";

export interface BadgeProps extends React.HTMLAttributes<HTMLDivElement> {
  variant?: "default" | "cyan" | "ice" | "secondary" | "outline" | "success" | "warning";
}

function Badge({
  className,
  variant = "default",
  ...props
}: BadgeProps) {
  const variantStyles = {
    default: "bg-cyan-500/15 text-cyan-300 border-cyan-500/30 shadow-[0_0_12px_rgba(0,240,255,0.1)]",
    cyan: "bg-cyan-400/15 text-cyan-300 border-cyan-400/30",
    ice: "bg-sky-400/15 text-sky-300 border-sky-400/30",
    secondary: "bg-slate-800/80 text-slate-300 border-white/10",
    outline: "text-slate-300 border-white/10 bg-transparent",
    success: "bg-teal-500/15 text-teal-300 border-teal-500/30",
    warning: "bg-amber-500/15 text-amber-300 border-amber-500/30",
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

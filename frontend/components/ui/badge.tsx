import * as React from "react";
import { cn } from "@/lib/utils";

export interface BadgeProps extends React.HTMLAttributes<HTMLDivElement> {
  variant?: "default" | "secondary" | "outline" | "success" | "warning";
}

function Badge({
  className,
  variant = "default",
  ...props
}: BadgeProps) {
  const variantStyles = {
    default: "bg-emerald-500/15 text-emerald-400 border-emerald-500/30",
    secondary: "bg-slate-800 text-slate-300 border-slate-700",
    outline: "text-slate-300 border-slate-700",
    success: "bg-teal-500/15 text-teal-300 border-teal-500/30",
    warning: "bg-amber-500/15 text-amber-300 border-amber-500/30",
  };

  return (
    <div
      className={cn(
        "inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-semibold transition-colors",
        variantStyles[variant],
        className
      )}
      {...props}
    />
  );
}

export { Badge };

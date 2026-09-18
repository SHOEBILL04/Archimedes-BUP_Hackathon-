import * as React from "react";
import { cn } from "@/lib/utils";

export interface BadgeProps extends React.HTMLAttributes<HTMLDivElement> {
  variant?:
    | "default"
    | "sage"
    | "copper"
    | "slate"
    | "mist"
    | "emerald"
    | "cyan"
    | "amber"
    | "indigo"
    | "coral"
    | "hero"
    | "hero-cyan"
    | "secondary"
    | "outline";
}

function Badge({
  className,
  variant = "default",
  ...props
}: BadgeProps) {
  const variantStyles = {
    default: "bg-[#E8EFE9] text-[#1C312E] border-[rgba(28,49,46,0.14)] font-semibold",
    // Solar & Optimum Status (Sage Green on Cool Mist)
    sage: "bg-[#E8EFE9] text-[#4E8773] border-[#4E8773]/30 font-semibold",
    // Battery Discharge / Limit Warning (Terracotta / Earthy Copper)
    copper: "bg-[#D97757]/12 text-[#D97757] border-[#D97757]/30 font-semibold",
    slate: "bg-[#1C312E]/08 text-[#1C312E] border-[#1C312E]/15 font-semibold",
    mist: "bg-[#E8EFE9] text-[#1C312E] border-[rgba(28,49,46,0.14)] font-semibold",
    // Compatibility aliases
    emerald: "bg-[#E8EFE9] text-[#4E8773] border-[#4E8773]/30 font-semibold",
    cyan: "bg-[#E8EFE9] text-[#4E8773] border-[#4E8773]/25 font-semibold",
    amber: "bg-[#D97757]/12 text-[#D97757] border-[#D97757]/30 font-semibold",
    indigo: "bg-[#1C312E]/08 text-[#1C312E] border-[#1C312E]/15 font-semibold",
    coral: "bg-[#D97757]/12 text-[#D97757] border-[#D97757]/30 font-semibold",
    hero: "bg-[#E8EFE9] text-[#4E8773] border-[#4E8773]/30 font-semibold",
    "hero-cyan": "bg-[#D97757]/12 text-[#D97757] border-[#D97757]/30 font-semibold",
    secondary: "bg-[#F4F7F4] text-[#1C312E] border-[rgba(28,49,46,0.08)]",
    outline: "text-[#1C312E] border-[rgba(28,49,46,0.15)] bg-white",
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

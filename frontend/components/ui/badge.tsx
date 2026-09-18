import * as React from "react";
import { cn } from "@/lib/utils";

export type BadgeVariant =
  | "default"
  | "brand"
  | "accent"
  | "cream"
  | "coral"
  | "neutral"
  | "outline";

export interface BadgeProps extends React.HTMLAttributes<HTMLDivElement> {
  variant?: BadgeVariant;
}

/**
 * Every badge pairs a pastel/tinted surface with its matching ink, keeping all
 * combinations above 4.5:1. The four brand hues cover the full semantic range,
 * so no off-palette success/warning colors are introduced.
 */
const variantStyles: Record<BadgeVariant, string> = {
  default: "bg-brand-50 text-brand border-brand/20 font-semibold",
  brand: "bg-brand-50 text-brand border-brand/25 font-semibold",
  accent: "bg-accent-100 text-accent-ink border-accent/40 font-semibold",
  cream: "bg-cream text-cream-ink border-cream-ink/25 font-semibold",
  coral: "bg-coral-50 text-coral-ink border-coral/50 font-bold",
  neutral: "bg-canvas text-ink-muted border-line font-medium",
  outline: "bg-surface text-ink-muted border-line font-medium",
};

function Badge({ className, variant = "default", ...props }: BadgeProps) {
  return (
    <div
      className={cn(
        "inline-flex items-center rounded-full border px-2.5 py-0.5 text-[11px] tracking-tight transition-colors",
        variantStyles[variant],
        className
      )}
      {...props}
    />
  );
}

export { Badge };

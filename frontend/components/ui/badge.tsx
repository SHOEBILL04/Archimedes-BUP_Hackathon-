import * as React from "react";
import { cn } from "@/lib/utils";

export interface BadgeProps extends React.HTMLAttributes<HTMLDivElement> {
  variant?: "default" | "indigo" | "sky" | "cream" | "coral" | "secondary" | "outline" | "success" | "warning";
}

function Badge({
  className,
  variant = "default",
  ...props
}: BadgeProps) {
  const variantStyles = {
    default: "bg-[#425B9A]/10 text-[#425B9A] border-[#425B9A]/20 font-semibold",
    indigo: "bg-[#425B9A]/10 text-[#425B9A] border-[#425B9A]/25 font-semibold",
    sky: "bg-[#76C0EC]/20 text-[#254b7c] border-[#76C0EC]/40 font-semibold",
    cream: "bg-[#FFF6DC] text-[#78590c] border-[#f5e4ab] font-semibold",
    coral: "bg-[#FF95A5]/25 text-[#b91c38] border-[#FF95A5]/45 font-bold",
    secondary: "bg-slate-100 text-slate-700 border-slate-200",
    outline: "text-slate-600 border-slate-200 bg-white",
    success: "bg-emerald-50 text-emerald-700 border-emerald-200 font-semibold",
    warning: "bg-amber-50 text-amber-800 border-amber-200 font-semibold",
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

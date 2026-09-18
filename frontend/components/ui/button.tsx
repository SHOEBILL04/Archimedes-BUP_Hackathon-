import * as React from "react";
import { cn } from "@/lib/utils";

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?:
    | "default"
    | "emerald"
    | "cyan"
    | "indigo"
    | "sky"
    | "coral"
    | "outline"
    | "secondary"
    | "ghost"
    | "destructive";
  size?: "default" | "sm" | "lg" | "icon";
}

const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant = "default", size = "default", ...props }, ref) => {
    const baseStyles =
      "inline-flex items-center justify-center whitespace-nowrap rounded-xl text-sm font-medium transition-all duration-200 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-slate-900/20 disabled:pointer-events-none disabled:opacity-50 select-none cursor-pointer";

    const variantStyles = {
      default:
        "bg-[#0F172A] text-white font-semibold shadow-xs hover:bg-slate-800 active:scale-[0.98]",
      emerald:
        "bg-[#059669] text-white font-semibold shadow-xs hover:bg-[#047857] active:scale-[0.98]",
      cyan:
        "bg-[#0284C7] text-white font-semibold shadow-xs hover:bg-[#0369A1] active:scale-[0.98]",
      indigo:
        "bg-[#4F46E5] text-white font-semibold shadow-xs hover:bg-[#4338CA] active:scale-[0.98]",
      sky:
        "bg-sky-50 text-sky-700 font-semibold border border-sky-200 hover:bg-sky-100 active:scale-[0.98]",
      coral:
        "bg-rose-600 text-white font-semibold shadow-xs hover:bg-rose-700 active:scale-[0.98]",
      outline:
        "border border-slate-200 bg-white text-slate-700 font-medium shadow-2xs hover:bg-slate-50 hover:border-slate-300 hover:text-slate-900 active:scale-[0.98]",
      secondary:
        "bg-slate-100 text-slate-800 font-medium hover:bg-slate-200 active:scale-[0.98]",
      ghost: "hover:bg-slate-100 text-slate-600 hover:text-slate-900 font-medium",
      destructive:
        "bg-rose-600 text-white shadow-xs hover:bg-rose-700 active:scale-[0.98]",
    };

    const sizeStyles = {
      default: "h-10 px-4 py-2",
      sm: "h-8 rounded-lg px-3 text-xs",
      lg: "h-11 rounded-xl px-7 text-sm",
      icon: "h-9 w-9 rounded-lg",
    };

    return (
      <button
        className={cn(
          baseStyles,
          variantStyles[variant],
          sizeStyles[size],
          className
        )}
        ref={ref}
        {...props}
      />
    );
  }
);
Button.displayName = "Button";

export { Button };

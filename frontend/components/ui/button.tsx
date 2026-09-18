import * as React from "react";
import { cn } from "@/lib/utils";

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "default" | "cyan" | "outline" | "secondary" | "ghost" | "destructive";
  size?: "default" | "sm" | "lg" | "icon";
}

const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant = "default", size = "default", ...props }, ref) => {
    const baseStyles =
      "inline-flex items-center justify-center whitespace-nowrap rounded-xl text-sm font-medium transition-all duration-200 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyan-400 disabled:pointer-events-none disabled:opacity-50 select-none cursor-pointer";

    const variantStyles = {
      default:
        "bg-gradient-to-r from-cyan-400 via-sky-400 to-blue-500 text-slate-950 font-semibold shadow-md shadow-cyan-500/20 hover:shadow-lg hover:shadow-cyan-500/30 hover:brightness-110 active:scale-[0.98]",
      cyan:
        "bg-cyan-400 text-slate-950 font-semibold shadow-md shadow-cyan-400/20 hover:bg-cyan-300 hover:shadow-cyan-400/30 active:scale-[0.98]",
      outline:
        "border border-white/10 bg-slate-900/40 text-slate-200 hover:border-cyan-500/40 hover:bg-slate-800/60 hover:text-cyan-300 active:scale-[0.98]",
      secondary:
        "bg-slate-800/80 border border-white/[0.06] text-slate-200 shadow-sm hover:bg-slate-800 hover:text-white active:scale-[0.98]",
      ghost: "hover:bg-slate-800/60 text-slate-300 hover:text-white",
      destructive:
        "bg-rose-500/90 text-white shadow-sm hover:bg-rose-500 active:scale-[0.98]",
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

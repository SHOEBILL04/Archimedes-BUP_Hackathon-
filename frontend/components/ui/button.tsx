import * as React from "react";
import { cn } from "@/lib/utils";

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "default" | "indigo" | "sky" | "coral" | "outline" | "secondary" | "ghost" | "destructive";
  size?: "default" | "sm" | "lg" | "icon";
}

const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant = "default", size = "default", ...props }, ref) => {
    const baseStyles =
      "inline-flex items-center justify-center whitespace-nowrap rounded-xl text-sm font-medium transition-all duration-200 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#425B9A] disabled:pointer-events-none disabled:opacity-50 select-none cursor-pointer";

    const variantStyles = {
      default:
        "bg-[#425B9A] text-white font-semibold shadow-sm hover:bg-[#35497d] active:scale-[0.98]",
      indigo:
        "bg-[#425B9A] text-white font-semibold shadow-sm hover:bg-[#35497d] active:scale-[0.98]",
      sky:
        "bg-[#76C0EC]/25 text-[#2c477f] font-semibold border border-[#76C0EC]/40 hover:bg-[#76C0EC]/40 active:scale-[0.98]",
      coral:
        "bg-[#FF95A5] text-[#1E293B] font-bold shadow-sm hover:bg-[#ff8093] hover:text-white active:scale-[0.98]",
      outline:
        "border border-slate-200 bg-white text-[#425B9A] font-medium shadow-xs hover:bg-[#F8FAFC] hover:border-[#425B9A]/30 active:scale-[0.98]",
      secondary:
        "bg-[#F1F5F9] text-slate-700 font-medium hover:bg-[#E2E8F0] active:scale-[0.98]",
      ghost: "hover:bg-[#425B9A]/10 text-[#425B9A] font-medium",
      destructive:
        "bg-rose-500 text-white shadow-xs hover:bg-rose-600 active:scale-[0.98]",
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

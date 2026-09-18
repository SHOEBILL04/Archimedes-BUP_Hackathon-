import * as React from "react";
import { cn } from "@/lib/utils";

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?:
    | "default"
    | "sage"
    | "copper"
    | "slate"
    | "mist"
    | "emerald"
    | "cyan"
    | "indigo"
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
      "inline-flex items-center justify-center whitespace-nowrap rounded-xl text-sm font-medium transition-all duration-200 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#4E8773]/30 disabled:pointer-events-none disabled:opacity-50 select-none cursor-pointer";

    const variantStyles = {
      default:
        "bg-[#1C312E] text-[#FAFCFA] font-semibold shadow-xs hover:bg-[#2A4742] active:scale-[0.98]",
      slate:
        "bg-[#1C312E] text-[#FAFCFA] font-semibold shadow-xs hover:bg-[#2A4742] active:scale-[0.98]",
      sage:
        "bg-[#4E8773] text-white font-semibold shadow-xs hover:bg-[#3E6F5E] active:scale-[0.98]",
      copper:
        "bg-[#D97757] text-white font-semibold shadow-xs hover:bg-[#C26243] active:scale-[0.98]",
      mist:
        "bg-[#E8EFE9] text-[#1C312E] font-semibold border border-[rgba(28,49,46,0.12)] hover:bg-[#DCE6DE] active:scale-[0.98]",
      emerald:
        "bg-[#4E8773] text-white font-semibold shadow-xs hover:bg-[#3E6F5E] active:scale-[0.98]",
      cyan:
        "bg-[#E8EFE9] text-[#1C312E] font-semibold border border-[rgba(28,49,46,0.12)] hover:bg-[#DCE6DE] active:scale-[0.98]",
      indigo:
        "bg-[#1C312E] text-[#FAFCFA] font-semibold shadow-xs hover:bg-[#2A4742] active:scale-[0.98]",
      coral:
        "bg-[#D97757] text-white font-semibold shadow-xs hover:bg-[#C26243] active:scale-[0.98]",
      outline:
        "border border-[rgba(28,49,46,0.15)] bg-white text-[#1C312E] font-medium shadow-2xs hover:bg-[#F4F7F4] hover:border-[rgba(28,49,46,0.25)] active:scale-[0.98]",
      secondary:
        "bg-[#F4F7F4] text-[#1C312E] font-medium hover:bg-[#E8EFE9] active:scale-[0.98]",
      ghost: "hover:bg-[#E8EFE9]/70 text-[#1C312E] font-medium",
      destructive:
        "bg-[#D97757] text-white shadow-xs hover:bg-[#C26243] active:scale-[0.98]",
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

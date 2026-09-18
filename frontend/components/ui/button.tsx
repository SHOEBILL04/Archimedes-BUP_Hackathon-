import * as React from "react";
import { cn } from "@/lib/utils";

export type ButtonVariant =
  | "default"
  | "brand"
  | "accent"
  | "coral"
  | "outline"
  | "secondary"
  | "ghost";

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant;
  size?: "default" | "sm" | "lg" | "icon";
}

const baseStyles =
  "inline-flex cursor-pointer select-none items-center justify-center whitespace-nowrap rounded-xl text-sm font-medium transition-all duration-200 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-brand disabled:pointer-events-none disabled:opacity-50 active:scale-[0.98] motion-reduce:active:scale-100";

/**
 * Pastel fills (accent/coral) pair with `text-ink`, never white — white on
 * either sits at ~2:1 and fails AA. Solid brand fills carry white at 6.6:1.
 */
const variantStyles: Record<ButtonVariant, string> = {
  default: "bg-brand text-white font-semibold shadow-tile hover:bg-brand-600",
  brand: "bg-brand text-white font-semibold shadow-tile hover:bg-brand-600",
  accent:
    "bg-accent-100 text-accent-ink font-semibold border border-accent/45 hover:bg-accent-200 hover:border-accent",
  coral:
    "bg-coral text-ink font-bold shadow-tile hover:bg-coral-600 hover:shadow-bento",
  outline:
    "border border-line bg-surface text-brand font-medium shadow-tile hover:bg-brand-50 hover:border-brand/35",
  secondary:
    "bg-canvas text-ink-muted font-medium border border-line hover:bg-brand-50 hover:text-brand",
  ghost: "text-brand font-medium hover:bg-brand-50",
};

const sizeStyles = {
  default: "h-10 px-4 py-2",
  sm: "h-8 rounded-lg px-3 text-xs",
  lg: "h-11 rounded-xl px-7 text-sm",
  icon: "h-9 w-9 rounded-lg",
};

const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant = "default", size = "default", ...props }, ref) => (
    <button
      ref={ref}
      className={cn(
        baseStyles,
        variantStyles[variant],
        sizeStyles[size],
        className
      )}
      {...props}
    />
  )
);
Button.displayName = "Button";

export { Button };

import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

/** Merge conditional class names, resolving conflicting Tailwind utilities. */
export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

/** Format a BDT amount for display, e.g. 9850 -> "৳9,850.00". */
export function formatCurrencyBDT(value: number): string {
  if (!Number.isFinite(value)) {
    return "—";
  }
  return `৳${value.toLocaleString("en-US", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })}`;
}

/** Format a numeric telemetry value with a fixed number of decimals. */
export function formatNumber(value: number, digits = 0): string {
  if (!Number.isFinite(value)) {
    return "—";
  }
  return value.toLocaleString("en-US", {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  });
}

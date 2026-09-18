/**
 * JS mirror of the `@theme` block in `app/globals.css`.
 *
 * Recharts renders SVG presentation attributes (`stroke`, `stopColor`) which
 * cannot resolve CSS custom properties, so chart marks need literal values.
 * This module is the ONLY place a color literal may appear outside globals.css
 * — components import from here instead of hardcoding hex.
 *
 * Accessibility contract (verified against WCAG 2.1):
 *   - Pastels (accent/cream/coral) are SURFACES only: ~2:1 on white, so they
 *     fail both 4.5:1 for text and 3:1 for data-bearing strokes.
 *   - `*Ink` variants are MARKS: same hue, darkened past 4.5:1 on white.
 * Chart series therefore stroke with inks and fill with pastels.
 */

export const palette = {
  brand: "#425B9A",
  brandLight: "#6A82B8",
  brandDark: "#374C81",

  accent: "#76C0EC",
  accentInk: "#17698F",

  cream: "#FFF6DC",
  creamInk: "#8A6700",

  coral: "#FF95A5",
  coralInk: "#C43E58",

  canvas: "#F8FAFC",
  surface: "#FFFFFF",
  line: "#E2E8F0",
  ink: "#1E293B",
  inkMuted: "#475569",
  inkSubtle: "#64748B",
} as const;

/** Semantic color per chart series, so the same quantity reads identically everywhere. */
export const seriesColor = {
  demand: palette.accentInk,
  grid: palette.brand,
  solarPotential: palette.creamInk,
  solarDispatched: palette.accentInk,
  batterySoc: palette.brand,
  charge: palette.accentInk,
  discharge: palette.coralInk,
} as const;

/** Shared Recharts axis/grid styling. */
export const chartAxis = {
  stroke: palette.inkMuted,
  fontSize: 10,
  tickLine: false,
} as const;

export const chartGrid = {
  strokeDasharray: "3 3",
  stroke: palette.line,
} as const;

/** Tooltip surface matching the bento card treatment. */
export const chartTooltipStyle: React.CSSProperties = {
  backgroundColor: palette.surface,
  border: `1px solid ${palette.line}`,
  borderRadius: "0.75rem",
  fontSize: "11px",
  fontFamily: "var(--font-mono)",
  color: palette.ink,
  boxShadow: "0 10px 28px -4px rgb(66 91 154 / 0.18)",
};

export const chartLegendStyle: React.CSSProperties = {
  fontSize: "11px",
  fontFamily: "var(--font-mono)",
  paddingTop: "8px",
};

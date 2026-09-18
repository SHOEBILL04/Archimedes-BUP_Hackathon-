import React from "react";

interface LogoProps extends React.SVGProps<SVGSVGElement> {
  className?: string;
}

/**
 * The Archimedean Balance Logomark Icon (Clean-Tech Palette: Midnight Slate, Emerald, Electric Cyan)
 */
export function ArchimedesIcon({ className, ...props }: LogoProps) {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      viewBox="0 0 136 140"
      fill="none"
      className={className}
      {...props}
    >
      {/* Outer Equilibrium Orbit / Ring */}
      <circle
        cx="68"
        cy="70"
        r="46"
        fill="none"
        stroke="#0EA5E9"
        strokeOpacity="0.25"
        strokeWidth="2"
        strokeDasharray="4 4"
      />

      {/* Solar / Clean Renewable Arc (Emerald #10B981) */}
      <path
        d="M 68 24 A 46 46 0 0 1 114 70"
        fill="none"
        stroke="#10B981"
        strokeWidth="5"
        strokeLinecap="round"
      />

      {/* Smart Grid / Storage Arc (Electric Cyan #0EA5E9) */}
      <path
        d="M 68 116 A 46 46 0 0 1 22 70"
        fill="none"
        stroke="#0EA5E9"
        strokeWidth="5"
        strokeLinecap="round"
      />

      {/* The Fulcrum Base Plate: Slate Ice (#F1F5F9) */}
      <circle cx="68" cy="70" r="28" fill="#F1F5F9" stroke="#E2E8F0" strokeWidth="1.5" />

      {/* The Archimedes "A" Fulcrum (Midnight Slate #0F172A) */}
      <polygon points="68,46 54,78 82,78" fill="#0F172A" />

      {/* Fulcrum Cross-Tie Cutout */}
      <line x1="57" y1="71" x2="79" y2="71" stroke="#F1F5F9" strokeWidth="2.5" />

      {/* Energy Balance Nodes */}
      <circle cx="68" cy="24" r="4" fill="#10B981" />
      <circle cx="68" cy="116" r="4" fill="#0EA5E9" />
      <circle cx="68" cy="55" r="2.5" fill="#10B981" />
    </svg>
  );
}

/**
 * The Full Archimedes Brand Header (Logomark + Wordmark + Tag) in Clean-Tech Palette
 */
export function ArchimedesLogo({ className, ...props }: LogoProps) {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      viewBox="0 0 540 140"
      width="100%"
      height="100%"
      className={className}
      {...props}
    >
      {/* ================= LOGOMARK: THE ARCHIMEDEAN BALANCE ================= */}
      {/* Outer Equilibrium Orbit / Ring */}
      <circle
        cx="68"
        cy="70"
        r="46"
        fill="none"
        stroke="#0EA5E9"
        strokeOpacity="0.25"
        strokeWidth="2"
        strokeDasharray="4 4"
      />

      {/* Solar / Renewable Arc (Emerald #10B981) */}
      <path
        d="M 68 24 A 46 46 0 0 1 114 70"
        fill="none"
        stroke="#10B981"
        strokeWidth="5"
        strokeLinecap="round"
      />

      {/* Smart Grid / Storage Arc (Electric Cyan #0EA5E9) */}
      <path
        d="M 68 116 A 46 46 0 0 1 22 70"
        fill="none"
        stroke="#0EA5E9"
        strokeWidth="5"
        strokeLinecap="round"
      />

      {/* The Fulcrum Base Plate: Slate Ice (#F1F5F9) */}
      <circle cx="68" cy="70" r="28" fill="#F1F5F9" stroke="#E2E8F0" strokeWidth="1.5" />

      {/* The Archimedes "A" Fulcrum (Midnight Slate #0F172A) */}
      <polygon points="68,46 54,78 82,78" fill="#0F172A" />

      {/* Fulcrum Cross-Tie Cutout */}
      <line x1="57" y1="71" x2="79" y2="71" stroke="#F1F5F9" strokeWidth="2.5" />

      {/* Energy Balance Nodes */}
      <circle cx="68" cy="24" r="4" fill="#10B981" />
      <circle cx="68" cy="116" r="4" fill="#0EA5E9" />
      <circle cx="68" cy="55" r="2.5" fill="#10B981" />

      {/* ================= TYPOGRAPHY & WORDMARK ================= */}
      {/* Main Brand Title */}
      <text
        x="148"
        y="72"
        fontFamily="system-ui, -apple-system, 'Inter', 'Segoe UI', sans-serif"
        fontSize="38"
        fontWeight="800"
        letterSpacing="-0.04em"
        fill="#0F172A"
      >
        Archimedes
      </text>

      {/* Accent Indicator Dot (Clean Energy Emerald) */}
      <circle cx="376" cy="65" r="4" fill="#10B981" />

      {/* Meta Subtitle (Electric Cyan) */}
      <text
        x="150"
        y="96"
        fontFamily="system-ui, -apple-system, 'Inter', 'Segoe UI', monospace"
        fontSize="11"
        fontWeight="700"
        letterSpacing="0.18em"
        fill="#0EA5E9"
      >
        SMART ENERGY EQUILIBRIUM
      </text>

      {/* Status / Pill Tag */}
      <rect
        x="440"
        y="52"
        width="62"
        height="22"
        rx="6"
        fill="#F1F5F9"
        stroke="#0F172A"
        strokeOpacity="0.15"
        strokeWidth="1.2"
      />
      <text
        x="471"
        y="67"
        fontFamily="system-ui, -apple-system, monospace"
        fontSize="10"
        fontWeight="700"
        letterSpacing="0.06em"
        fill="#0F172A"
        textAnchor="middle"
      >
        LP · 24H
      </text>
    </svg>
  );
}

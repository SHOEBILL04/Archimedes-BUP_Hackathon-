import React from "react";

interface LogoProps extends React.SVGProps<SVGSVGElement> {
  className?: string;
}

/**
 * The Archimedean Balance Logomark Icon (Icon Only)
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
        stroke="#4E8773"
        strokeOpacity="0.22"
        strokeWidth="2"
        strokeDasharray="4 4"
      />

      {/* Solar / Renewable Arc (#4E8773 Sage Green) */}
      <path
        d="M 68 24 A 46 46 0 0 1 114 70"
        fill="none"
        stroke="#4E8773"
        strokeWidth="5"
        strokeLinecap="round"
      />

      {/* Storage / Discharge Arc (#D97757 Earthy Copper) */}
      <path
        d="M 68 116 A 46 46 0 0 1 22 70"
        fill="none"
        stroke="#D97757"
        strokeWidth="5"
        strokeLinecap="round"
      />

      {/* The Fulcrum Base Plate: Cool Mist (#E8EFE9) */}
      <circle cx="68" cy="70" r="28" fill="#E8EFE9" />

      {/* The Archimedes "A" Fulcrum (Slate Forest #1C312E) */}
      <polygon points="68,46 54,78 82,78" fill="#1C312E" />

      {/* Fulcrum Cross-Tie Cutout */}
      <line x1="57" y1="71" x2="79" y2="71" stroke="#E8EFE9" strokeWidth="2" />

      {/* Energy Balance Nodes */}
      <circle cx="68" cy="24" r="4" fill="#4E8773" />
      <circle cx="68" cy="116" r="4" fill="#D97757" />
      <circle cx="68" cy="55" r="2.5" fill="#E8EFE9" />
    </svg>
  );
}

/**
 * The Full Archimedes Brand Header (Logomark + Wordmark + Tag)
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
        stroke="#4E8773"
        strokeOpacity="0.22"
        strokeWidth="2"
        strokeDasharray="4 4"
      />

      {/* Solar / Renewable Arc (#4E8773 Sage Green) */}
      <path
        d="M 68 24 A 46 46 0 0 1 114 70"
        fill="none"
        stroke="#4E8773"
        strokeWidth="5"
        strokeLinecap="round"
      />

      {/* Storage / Discharge Arc (#D97757 Earthy Copper) */}
      <path
        d="M 68 116 A 46 46 0 0 1 22 70"
        fill="none"
        stroke="#D97757"
        strokeWidth="5"
        strokeLinecap="round"
      />

      {/* The Fulcrum Base Plate: Cool Mist (#E8EFE9) */}
      <circle cx="68" cy="70" r="28" fill="#E8EFE9" />

      {/* The Archimedes "A" Fulcrum (Slate Forest #1C312E) */}
      <polygon points="68,46 54,78 82,78" fill="#1C312E" />

      {/* Fulcrum Cross-Tie Cutout */}
      <line x1="57" y1="71" x2="79" y2="71" stroke="#E8EFE9" strokeWidth="2" />

      {/* Energy Balance Nodes */}
      <circle cx="68" cy="24" r="4" fill="#4E8773" />
      <circle cx="68" cy="116" r="4" fill="#D97757" />
      <circle cx="68" cy="55" r="2.5" fill="#E8EFE9" />

      {/* ================= TYPOGRAPHY & WORDMARK ================= */}
      {/* Main Brand Title */}
      <text
        x="148"
        y="72"
        fontFamily="system-ui, -apple-system, 'Inter', 'Segoe UI', sans-serif"
        fontSize="38"
        fontWeight="800"
        letterSpacing="-0.04em"
        fill="#1C312E"
      >
        Archimedes
      </text>

      {/* Accent Indicator Dot */}
      <circle cx="376" cy="65" r="4" fill="#D97757" />

      {/* Meta Subtitle */}
      <text
        x="150"
        y="96"
        fontFamily="system-ui, -apple-system, 'Inter', 'Segoe UI', monospace"
        fontSize="11"
        fontWeight="700"
        letterSpacing="0.18em"
        fill="#4E8773"
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
        fill="#E8EFE9"
        stroke="#1C312E"
        strokeOpacity="0.12"
        strokeWidth="1.2"
      />
      <text
        x="471"
        y="67"
        fontFamily="system-ui, -apple-system, monospace"
        fontSize="10"
        fontWeight="700"
        letterSpacing="0.06em"
        fill="#1C312E"
        textAnchor="middle"
      >
        LP · 24H
      </text>
    </svg>
  );
}

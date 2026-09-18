import React from "react";

interface LogoProps extends React.SVGProps<SVGSVGElement> {
  className?: string;
}

/**
 * Minimal, Work-Focused Archimedes Logomark (Clean-Tech: Midnight Slate, Emerald, Electric Cyan)
 * Features the geometric "A" energy fulcrum in equilibrium balance.
 */
export function ArchimedesIcon({ className, ...props }: LogoProps) {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      viewBox="0 0 100 100"
      fill="none"
      className={className}
      {...props}
    >
      <defs>
        <linearGradient id="arch-bg" x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" stopColor="#0F172A" />
          <stop offset="100%" stopColor="#1E293B" />
        </linearGradient>
        <linearGradient id="arch-emerald" x1="0%" y1="100%" x2="50%" y2="0%">
          <stop offset="0%" stopColor="#059669" />
          <stop offset="100%" stopColor="#10B981" />
        </linearGradient>
        <linearGradient id="arch-cyan" x1="50%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" stopColor="#38BDF8" />
          <stop offset="100%" stopColor="#0284C7" />
        </linearGradient>
      </defs>

      {/* Modern Work-Focused Squircle Container */}
      <rect width="100" height="100" rx="22" fill="url(#arch-bg)" />
      <rect
        x="1.5"
        y="1.5"
        width="97"
        height="97"
        rx="20.5"
        fill="none"
        stroke="#334155"
        strokeWidth="1.5"
        strokeOpacity="0.6"
      />

      {/* Subtle Coordinate Crosshair for Mathematical LP Optimization */}
      <line
        x1="22"
        y1="52"
        x2="78"
        y2="52"
        stroke="#334155"
        strokeWidth="1"
        strokeDasharray="2 3"
        strokeOpacity="0.4"
      />
      <line
        x1="50"
        y1="22"
        x2="50"
        y2="78"
        stroke="#334155"
        strokeWidth="1"
        strokeDasharray="2 3"
        strokeOpacity="0.4"
      />

      {/* The Archimedean "A" Fulcrum Apex & Arms */}
      <path
        d="M 31 73 L 50 25"
        stroke="url(#arch-emerald)"
        strokeWidth="6.5"
        strokeLinecap="round"
      />
      <path
        d="M 50 25 L 69 73"
        stroke="url(#arch-cyan)"
        strokeWidth="6.5"
        strokeLinecap="round"
      />

      {/* Horizontal Energy Equilibrium Balance Beam */}
      <path
        d="M 23 52 L 77 52"
        stroke="#FFFFFF"
        strokeWidth="4"
        strokeLinecap="round"
      />

      {/* Center Optimal Nexus Node */}
      <circle cx="50" cy="52" r="4.5" fill="#10B981" />
      <circle cx="50" cy="52" r="2" fill="#FFFFFF" />

      {/* Energy Balance Endpoints */}
      <circle cx="23" cy="52" r="2.8" fill="#10B981" />
      <circle cx="77" cy="52" r="2.8" fill="#38BDF8" />
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
      viewBox="0 0 460 100"
      fill="none"
      className={className}
      {...props}
    >
      <defs>
        <linearGradient id="arch-bg-full" x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" stopColor="#0F172A" />
          <stop offset="100%" stopColor="#1E293B" />
        </linearGradient>
        <linearGradient id="arch-emerald-full" x1="0%" y1="100%" x2="50%" y2="0%">
          <stop offset="0%" stopColor="#059669" />
          <stop offset="100%" stopColor="#10B981" />
        </linearGradient>
        <linearGradient id="arch-cyan-full" x1="50%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" stopColor="#38BDF8" />
          <stop offset="100%" stopColor="#0284C7" />
        </linearGradient>
      </defs>

      {/* Logomark Container */}
      <rect x="0" y="5" width="90" height="90" rx="20" fill="url(#arch-bg-full)" />
      <rect
        x="1"
        y="6"
        width="88"
        height="88"
        rx="19"
        fill="none"
        stroke="#334155"
        strokeWidth="1.5"
        strokeOpacity="0.6"
      />

      {/* The "A" Energy Fulcrum */}
      <path
        d="M 28 72 L 45 28"
        stroke="url(#arch-emerald-full)"
        strokeWidth="6"
        strokeLinecap="round"
      />
      <path
        d="M 45 28 L 62 72"
        stroke="url(#arch-cyan-full)"
        strokeWidth="6"
        strokeLinecap="round"
      />
      <path
        d="M 20 53 L 70 53"
        stroke="#FFFFFF"
        strokeWidth="3.5"
        strokeLinecap="round"
      />
      <circle cx="45" cy="53" r="4" fill="#10B981" />
      <circle cx="45" cy="53" r="1.8" fill="#FFFFFF" />

      {/* Typography */}
      <text
        x="108"
        y="54"
        fontFamily="system-ui, -apple-system, sans-serif"
        fontSize="34"
        fontWeight="800"
        letterSpacing="-0.04em"
        fill="#0F172A"
      >
        Archimedes
      </text>
      <circle cx="316" cy="46" r="3.5" fill="#10B981" />

      <text
        x="110"
        y="75"
        fontFamily="system-ui, -apple-system, monospace"
        fontSize="10"
        fontWeight="700"
        letterSpacing="0.16em"
        fill="#0EA5E9"
      >
        SMART ENERGY OPTIMIZATION
      </text>

      <rect
        x="340"
        y="36"
        width="58"
        height="20"
        rx="5"
        fill="#F1F5F9"
        stroke="#CBD5E1"
        strokeWidth="1"
      />
      <text
        x="369"
        y="50"
        fontFamily="system-ui, -apple-system, monospace"
        fontSize="9.5"
        fontWeight="700"
        letterSpacing="0.05em"
        fill="#334155"
        textAnchor="middle"
      >
        LP · 24H
      </text>
    </svg>
  );
}

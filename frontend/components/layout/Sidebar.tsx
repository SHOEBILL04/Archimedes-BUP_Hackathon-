"use client";

import React from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard,
  Sliders,
  FileText,
  Activity,
  Cpu,
  ExternalLink,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { ArchimedesIcon } from "./ArchimedesLogo";

const NAV_ITEMS = [
  {
    label: "Overview",
    href: "/",
    icon: LayoutDashboard,
  },
  {
    label: "Optimizer",
    href: "/dashboard",
    icon: Sliders,
  },
  {
    label: "FastAPI Docs",
    href: "http://localhost:8000/docs",
    icon: FileText,
    external: true,
  },
];

export function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="w-64 border-r border-[rgba(28,49,46,0.08)] bg-white flex flex-col justify-between shrink-0 min-h-screen">
      <div>
        {/* Brand Header with Archimedean Balance */}
        <div className="h-18 flex items-center gap-3 px-5 border-b border-[rgba(28,49,46,0.06)]">
          <div className="h-10 w-10 shrink-0">
            <ArchimedesIcon className="h-full w-full" />
          </div>
          <div className="min-w-0">
            <div className="flex items-center gap-1.5">
              <span className="text-base font-extrabold text-[#1C312E] tracking-tight">
                Archimedes
              </span>
              <span className="h-1.5 w-1.5 rounded-full bg-[#D97757]" />
              <span className="text-[10px] bg-[#E8EFE9] text-[#1C312E] border border-[rgba(28,49,46,0.1)] px-1.5 py-0.2 rounded font-mono font-bold">
                LP
              </span>
            </div>
            <p className="text-[9px] font-mono font-bold text-[#4E8773] tracking-widest truncate">
              SMART ENERGY EQUILIBRIUM
            </p>
          </div>
        </div>

        {/* Navigation Items */}
        <nav className="p-4 space-y-1.5">
          <div className="px-3 py-2 text-[10px] font-bold text-[#6E8480] uppercase tracking-wider font-mono">
            Platform Navigation
          </div>
          {NAV_ITEMS.map((item) => {
            const Icon = item.icon;
            const isActive = pathname === item.href;

            return (
              <Link
                key={item.label}
                href={item.href}
                target={item.external ? "_blank" : undefined}
                rel={item.external ? "noreferrer" : undefined}
                className={cn(
                  "flex items-center gap-3 px-3.5 py-2.5 rounded-xl text-xs font-semibold transition-all duration-200 group",
                  isActive
                    ? "bg-[#E8EFE9] text-[#1C312E] shadow-2xs border-l-2 border-[#4E8773]"
                    : "text-[#4A635E] hover:text-[#1C312E] hover:bg-[#F4F7F4]"
                )}
              >
                <Icon
                  className={cn(
                    "h-4 w-4 transition-colors",
                    isActive
                      ? "text-[#4E8773]"
                      : "text-[#6E8480] group-hover:text-[#1C312E]"
                  )}
                />
                <span>{item.label}</span>
                {item.external && (
                  <ExternalLink className="ml-auto h-3 w-3 text-[#6E8480] group-hover:text-[#1C312E]" />
                )}
              </Link>
            );
          })}
        </nav>
      </div>

      {/* Cool Mist System Equilibrium Card */}
      <div className="p-4 m-4 rounded-2xl border border-[rgba(28,49,46,0.12)] bg-[#E8EFE9] text-[#1C312E] shadow-2xs">
        <div className="flex items-center justify-between mb-2">
          <div className="flex items-center gap-2">
            <Cpu className="h-4 w-4 text-[#1C312E]" />
            <span className="text-xs font-bold text-[#1C312E]">Equilibrium Engine</span>
          </div>
          <span className="flex h-2 w-2 rounded-full bg-[#4E8773] ring-4 ring-[#4E8773]/25 animate-pulse" />
        </div>
        <p className="text-[11px] text-[#4A635E] mb-3 leading-relaxed">
          PuLP/CBC linear dispatch balancing solar generation and storage arbitrage.
        </p>
        <div className="flex items-center gap-2 text-[11px] text-[#4E8773] font-mono font-bold">
          <Activity className="h-3.5 w-3.5 text-[#4E8773]" />
          <span>Optimal & Verified</span>
        </div>
      </div>
    </aside>
  );
}

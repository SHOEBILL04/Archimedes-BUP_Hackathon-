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
    <aside className="w-64 border-r border-slate-200/90 bg-white flex flex-col justify-between shrink-0 min-h-screen">
      <div>
        {/* Brand Header with Archimedean Balance */}
        <div className="h-18 flex items-center gap-3 px-5 border-b border-slate-100">
          <div className="h-10 w-10 shrink-0">
            <ArchimedesIcon className="h-full w-full" />
          </div>
          <div className="min-w-0">
            <div className="flex items-center gap-1.5">
              <span className="text-base font-extrabold text-[#0F172A] tracking-tight">
                Archimedes
              </span>
              <span className="h-1.5 w-1.5 rounded-full bg-emerald-500" />
              <span className="text-[10px] bg-slate-100 text-slate-700 border border-slate-200 px-1.5 py-0.2 rounded font-mono font-bold">
                LP
              </span>
            </div>
            <p className="text-[9px] font-mono font-bold text-[#0EA5E9] tracking-widest truncate">
              SMART ENERGY EQUILIBRIUM
            </p>
          </div>
        </div>

        {/* Navigation Items */}
        <nav className="p-4 space-y-1.5">
          <div className="px-3 py-2 text-[10px] font-bold text-slate-400 uppercase tracking-wider font-mono">
            Navigation
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
                    ? "bg-[#0F172A] text-white shadow-xs"
                    : "text-slate-600 hover:text-slate-900 hover:bg-slate-50"
                )}
              >
                <Icon
                  className={cn(
                    "h-4 w-4 transition-colors",
                    isActive
                      ? "text-[#10B981]"
                      : "text-slate-400 group-hover:text-slate-700"
                  )}
                />
                <span>{item.label}</span>
                {item.external && (
                  <ExternalLink className="ml-auto h-3 w-3 text-slate-400 group-hover:text-slate-600" />
                )}
              </Link>
            );
          })}
        </nav>
      </div>

      {/* Clean Modern System Status Card */}
      <div className="p-4 m-4 rounded-2xl border border-slate-200 bg-slate-50/80 text-slate-800 shadow-2xs">
        <div className="flex items-center justify-between mb-2">
          <div className="flex items-center gap-2">
            <Cpu className="h-4 w-4 text-slate-700" />
            <span className="text-xs font-bold text-[#0F172A]">PuLP / CBC Engine</span>
          </div>
          <span className="flex h-2 w-2 rounded-full bg-[#10B981] ring-4 ring-[#10B981]/25 animate-pulse" />
        </div>
        <p className="text-[11px] text-slate-500 mb-3 leading-relaxed">
          Deterministic linear dispatch & replay verification active.
        </p>
        <div className="flex items-center gap-2 text-[11px] text-emerald-700 font-mono font-bold">
          <Activity className="h-3.5 w-3.5 text-emerald-600" />
          <span>Optimal & Feasible</span>
        </div>
      </div>
    </aside>
  );
}

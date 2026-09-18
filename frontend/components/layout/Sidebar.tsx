"use client";

import React from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  Zap,
  LayoutDashboard,
  Sliders,
  FileText,
  Activity,
  Cpu,
} from "lucide-react";
import { cn } from "@/lib/utils";

const NAV_ITEMS = [
  {
    label: "Dashboard",
    href: "/",
    icon: LayoutDashboard,
  },
  {
    label: "Optimizer",
    href: "/dashboard",
    icon: Sliders,
  },
  {
    label: "API Docs",
    href: "http://localhost:8000/docs",
    icon: FileText,
    external: true,
  },
];

export function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="w-64 border-r border-slate-800 bg-slate-950/80 backdrop-blur-xl flex flex-col justify-between shrink-0 min-h-screen">
      <div>
        {/* Brand Header */}
        <div className="h-16 flex items-center gap-3 px-6 border-b border-slate-800/80">
          <div className="h-9 w-9 rounded-lg bg-gradient-to-tr from-emerald-600 to-teal-400 flex items-center justify-center shadow-lg shadow-emerald-500/20 text-white font-bold">
            <Zap className="h-5 w-5 fill-current" />
          </div>
          <div>
            <h1 className="text-sm font-bold text-white tracking-wide">Archimedes</h1>
            <p className="text-[11px] text-slate-400">Smart Energy Engine</p>
          </div>
        </div>

        {/* Navigation Items */}
        <nav className="p-4 space-y-1.5">
          <div className="px-3 py-2 text-[11px] font-semibold text-slate-500 uppercase tracking-wider">
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
                  "flex items-center gap-3 px-3.5 py-2.5 rounded-lg text-sm font-medium transition-all group",
                  isActive
                    ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 shadow-sm"
                    : "text-slate-400 hover:text-slate-100 hover:bg-slate-900/80"
                )}
              >
                <Icon
                  className={cn(
                    "h-4 w-4 transition-colors",
                    isActive
                      ? "text-emerald-400"
                      : "text-slate-500 group-hover:text-slate-300"
                  )}
                />
                <span>{item.label}</span>
                {item.external && (
                  <span className="ml-auto text-[10px] bg-slate-800 text-slate-400 px-1.5 py-0.5 rounded">
                    ext
                  </span>
                )}
              </Link>
            );
          })}
        </nav>
      </div>

      {/* Footer / System Status card */}
      <div className="p-4 m-4 rounded-xl border border-slate-800 bg-slate-900/40">
        <div className="flex items-center gap-2 mb-2">
          <Cpu className="h-4 w-4 text-emerald-400" />
          <span className="text-xs font-semibold text-slate-300">LP Engine Status</span>
        </div>
        <p className="text-[11px] text-slate-400 mb-3 leading-relaxed">
          PuLP/CBC Linear Program Solver & LLM Directive Pipeline
        </p>
        <div className="flex items-center gap-2 text-[11px] text-emerald-400 font-medium">
          <Activity className="h-3.5 w-3.5 animate-pulse" />
          <span>Scaffold Ready</span>
        </div>
      </div>
    </aside>
  );
}

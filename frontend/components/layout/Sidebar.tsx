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
  ExternalLink,
} from "lucide-react";
import { cn } from "@/lib/utils";

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
    <aside className="w-64 border-r border-white/[0.07] bg-[#070b16]/80 backdrop-blur-2xl flex flex-col justify-between shrink-0 min-h-screen">
      <div>
        {/* Brand Header */}
        <div className="h-16 flex items-center gap-3 px-6 border-b border-white/[0.06]">
          <div className="h-9 w-9 rounded-xl bg-gradient-to-tr from-cyan-400 via-sky-500 to-blue-600 flex items-center justify-center shadow-lg shadow-cyan-500/20 text-slate-950 font-bold">
            <Zap className="h-5 w-5 fill-current text-slate-950" />
          </div>
          <div>
            <h1 className="text-sm font-bold text-white tracking-wide flex items-center gap-1.5">
              <span>Archimedes</span>
              <span className="text-[10px] text-cyan-400 font-mono font-normal">v1.0</span>
            </h1>
            <p className="text-[11px] text-slate-400 font-mono">Energy Platform</p>
          </div>
        </div>

        {/* Navigation Items */}
        <nav className="p-4 space-y-1.5">
          <div className="px-3 py-2 text-[10px] font-semibold text-slate-500 uppercase tracking-wider font-mono">
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
                  "flex items-center gap-3 px-3.5 py-2.5 rounded-xl text-xs font-medium transition-all duration-200 group",
                  isActive
                    ? "bg-cyan-500/10 text-cyan-300 border border-cyan-500/25 shadow-[0_0_15px_rgba(0,240,255,0.08)]"
                    : "text-slate-400 hover:text-slate-100 hover:bg-slate-800/40 hover:border hover:border-white/[0.05]"
                )}
              >
                <Icon
                  className={cn(
                    "h-4 w-4 transition-colors",
                    isActive
                      ? "text-cyan-400"
                      : "text-slate-500 group-hover:text-slate-300"
                  )}
                />
                <span>{item.label}</span>
                {item.external && (
                  <ExternalLink className="ml-auto h-3 w-3 text-slate-500 group-hover:text-slate-400" />
                )}
              </Link>
            );
          })}
        </nav>
      </div>

      {/* Footer System Status Bento Card */}
      <div className="p-4 m-4 rounded-2xl border border-white/[0.07] bg-slate-900/50 backdrop-blur-md">
        <div className="flex items-center justify-between mb-2">
          <div className="flex items-center gap-2">
            <Cpu className="h-3.5 w-3.5 text-cyan-400" />
            <span className="text-xs font-semibold text-slate-200">PuLP / CBC Engine</span>
          </div>
          <span className="flex h-2 w-2 rounded-full bg-cyan-400 animate-ping" />
        </div>
        <p className="text-[11px] text-slate-400 mb-3 leading-relaxed">
          Linear Programming dispatch with strict energy balance constraints.
        </p>
        <div className="flex items-center gap-2 text-[11px] text-cyan-400 font-mono">
          <Activity className="h-3 w-3" />
          <span>Pipeline Ready</span>
        </div>
      </div>
    </aside>
  );
}

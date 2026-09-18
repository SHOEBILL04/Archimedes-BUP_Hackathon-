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
    <aside className="w-64 border-r border-slate-200/90 bg-white flex flex-col justify-between shrink-0 min-h-screen">
      <div>
        {/* Brand Header */}
        <div className="h-16 flex items-center gap-3 px-6 border-b border-slate-100">
          <div className="h-9 w-9 rounded-xl bg-[#0F172A] flex items-center justify-center shadow-xs text-white font-bold">
            <Zap className="h-5 w-5 fill-[#10B981] text-[#10B981]" />
          </div>
          <div>
            <h1 className="text-sm font-bold text-[#0F172A] tracking-tight flex items-center gap-1.5">
              <span>GridWise</span>
              <span className="text-[10px] bg-emerald-50 text-emerald-700 border border-emerald-200 px-1.5 py-0.2 rounded-md font-mono font-semibold">LLM</span>
            </h1>
            <p className="text-[11px] text-slate-500 font-mono">Smart Campus Energy</p>
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

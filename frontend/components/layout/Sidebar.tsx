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
          <div className="h-9 w-9 rounded-xl bg-[#425B9A] flex items-center justify-center shadow-xs text-white font-bold">
            <Zap className="h-5 w-5 fill-[#76C0EC] text-[#76C0EC]" />
          </div>
          <div>
            <h1 className="text-sm font-bold text-[#425B9A] tracking-wide flex items-center gap-1.5">
              <span>Archimedes</span>
              <span className="text-[10px] bg-[#76C0EC]/20 text-[#254b7c] px-1.5 py-0.2 rounded font-mono font-medium">v1.0</span>
            </h1>
            <p className="text-[11px] text-slate-500 font-mono">Energy Platform</p>
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
                    ? "bg-[#425B9A] text-white shadow-sm"
                    : "text-slate-600 hover:text-[#425B9A] hover:bg-[#F8FAFC]"
                )}
              >
                <Icon
                  className={cn(
                    "h-4 w-4 transition-colors",
                    isActive
                      ? "text-[#76C0EC]"
                      : "text-slate-400 group-hover:text-[#425B9A]"
                  )}
                />
                <span>{item.label}</span>
                {item.external && (
                  <ExternalLink className="ml-auto h-3 w-3 text-slate-400 group-hover:text-[#425B9A]" />
                )}
              </Link>
            );
          })}
        </nav>
      </div>

      {/* Warm Cream Footer System Status Bento Card */}
      <div className="p-4 m-4 rounded-2xl border border-[#f5e4ab] bg-[#FFF6DC]/90 text-slate-800 shadow-xs">
        <div className="flex items-center justify-between mb-2">
          <div className="flex items-center gap-2">
            <Cpu className="h-4 w-4 text-[#425B9A]" />
            <span className="text-xs font-bold text-[#425B9A]">PuLP / CBC Engine</span>
          </div>
          <span className="flex h-2 w-2 rounded-full bg-[#76C0EC] ring-4 ring-[#76C0EC]/30 animate-pulse" />
        </div>
        <p className="text-[11px] text-slate-600 mb-3 leading-relaxed">
          Linear Programming dispatch ensuring zero physical balance error.
        </p>
        <div className="flex items-center gap-2 text-[11px] text-[#425B9A] font-mono font-bold">
          <Activity className="h-3.5 w-3.5 text-[#425B9A]" />
          <span>Pipeline Ready</span>
        </div>
      </div>
    </aside>
  );
}

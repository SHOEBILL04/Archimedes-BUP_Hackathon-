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
import { API_BASE_URL } from "@/lib/constants";

const NAV_ITEMS = [
  { label: "Overview", href: "/", icon: LayoutDashboard },
  { label: "Optimizer", href: "/dashboard", icon: Sliders },
  {
    label: "FastAPI Docs",
    href: `${API_BASE_URL}/docs`,
    icon: FileText,
    external: true,
  },
];

export function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="flex min-h-screen w-64 shrink-0 flex-col justify-between border-r border-line bg-surface">
      <div>
        {/* Brand mark */}
        <div className="flex h-16 items-center gap-3 border-b border-line px-6">
          <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-brand shadow-tile">
            <Zap className="h-5 w-5 fill-accent text-accent" />
          </div>
          <div>
            <h1 className="flex items-center gap-1.5 text-sm font-bold tracking-wide text-brand">
              <span>Archimedes</span>
              <span className="rounded bg-accent-100 px-1.5 py-px font-mono text-[10px] font-medium text-accent-ink">
                v1.0
              </span>
            </h1>
            <p className="font-mono text-[11px] text-ink-subtle">
              Energy Platform
            </p>
          </div>
        </div>

        {/* Navigation */}
        <nav className="space-y-1.5 p-4">
          <div className="px-3 py-2 font-mono text-[10px] font-bold uppercase tracking-wider text-ink-muted">
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
                aria-current={isActive ? "page" : undefined}
                className={cn(
                  "group flex items-center gap-3 rounded-xl px-3.5 py-2.5 text-xs font-semibold transition-all duration-200",
                  isActive
                    ? "bg-brand text-white shadow-tile"
                    : "text-ink-muted hover:bg-brand-50 hover:text-brand"
                )}
              >
                <Icon
                  className={cn(
                    "h-4 w-4 transition-colors",
                    isActive
                      ? "text-accent"
                      : "text-ink-subtle group-hover:text-brand"
                  )}
                />
                <span>{item.label}</span>
                {item.external && (
                  <ExternalLink className="ml-auto h-3 w-3 text-ink-subtle group-hover:text-brand" />
                )}
              </Link>
            );
          })}
        </nav>
      </div>

      {/* Warm cream engine-status block */}
      <div className="m-4 rounded-tile border border-brand/12 bg-cream p-4 shadow-tile">
        <div className="mb-2 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Cpu className="h-4 w-4 text-brand" />
            <span className="text-xs font-bold text-brand">
              PuLP / CBC Engine
            </span>
          </div>
          <span className="flex h-2 w-2 animate-pulse rounded-full bg-accent-600 ring-4 ring-accent/30" />
        </div>
        <p className="mb-3 text-[11px] leading-relaxed text-ink-muted">
          Linear Programming dispatch ensuring zero physical balance error.
        </p>
        <div className="flex items-center gap-2 font-mono text-[11px] font-bold text-brand">
          <Activity className="h-3.5 w-3.5" />
          <span>Pipeline Ready</span>
        </div>
      </div>
    </aside>
  );
}

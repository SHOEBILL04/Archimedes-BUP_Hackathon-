import React from "react";
import { Sidebar } from "./Sidebar";
import { Header } from "./Header";

interface PageContainerProps {
  children: React.ReactNode;
  title?: string;
}

export function PageContainer({ children, title }: PageContainerProps) {
  return (
    <div className="flex min-h-screen bg-slate-950 text-slate-100 font-sans antialiased selection:bg-emerald-500/30 selection:text-emerald-200">
      <Sidebar />
      <div className="flex-1 flex flex-col min-w-0">
        <Header title={title} />
        <main className="flex-1 p-8 max-w-7xl w-full mx-auto space-y-8">
          {children}
        </main>
      </div>
    </div>
  );
}

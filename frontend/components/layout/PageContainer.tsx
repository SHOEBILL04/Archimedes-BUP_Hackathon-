import React from "react";
import { Sidebar } from "./Sidebar";
import { Header } from "./Header";

interface PageContainerProps {
  children: React.ReactNode;
  title?: string;
}

export function PageContainer({ children, title }: PageContainerProps) {
  return (
    <div className="flex min-h-screen bg-[#050811] text-slate-100 font-sans antialiased selection:bg-cyan-500/30 selection:text-cyan-200">
      <Sidebar />
      <div className="flex-1 flex flex-col min-w-0">
        <Header title={title} />
        <main className="flex-1 p-5 sm:p-7 max-w-[1480px] w-full mx-auto space-y-6">
          {children}
        </main>
      </div>
    </div>
  );
}

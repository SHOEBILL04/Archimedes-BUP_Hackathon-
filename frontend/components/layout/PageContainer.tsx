import React from "react";
import { Sidebar } from "./Sidebar";
import { Header } from "./Header";

interface PageContainerProps {
  children: React.ReactNode;
  title?: string;
}

export function PageContainer({ children, title }: PageContainerProps) {
  return (
    <div className="flex min-h-screen bg-canvas font-sans text-ink antialiased">
      <Sidebar />
      <div className="flex min-w-0 flex-1 flex-col">
        <Header title={title} />
        <main className="mx-auto w-full max-w-[1480px] flex-1 space-y-6 p-5 sm:p-7">
          {children}
        </main>
      </div>
    </div>
  );
}

"use client";

import dynamic from "next/dynamic";
import { Sidebar } from "./Sidebar";

/**
 * CommandBar is modal and hidden by default — lazy-load its module
 * so it doesn't inflate the critical path bundle.
 */
const CommandBar = dynamic(
  () => import("@/components/ui/CommandBar").then((m) => m.CommandBar),
  { ssr: false },
);

interface AppShellProps {
  children: React.ReactNode;
}

export function AppShell({ children }: AppShellProps) {
  return (
    <div className="flex h-screen overflow-hidden bg-background">
      <Sidebar />
      <main className="flex-1 flex flex-col overflow-hidden">{children}</main>
      <CommandBar />
    </div>
  );
}

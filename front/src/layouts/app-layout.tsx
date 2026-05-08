import { Activity, Database, PanelsTopLeft } from "lucide-react";
import { NavLink, Outlet } from "react-router-dom";

import { Button } from "@/components/ui/button";

const navLinkClass = ({ isActive }: { isActive: boolean }) =>
  [
    "inline-flex h-9 items-center rounded-md px-3 text-sm font-medium transition-colors",
    isActive
      ? "bg-secondary text-secondary-foreground"
      : "text-muted-foreground hover:bg-secondary hover:text-secondary-foreground",
  ].join(" ");

export function AppLayout() {
  return (
    <div className="min-h-screen bg-background text-foreground">
      <header className="border-b bg-card">
        <div className="mx-auto flex h-16 max-w-6xl items-center justify-between gap-4 px-4 sm:px-6">
          <div className="flex items-center gap-3">
            <div className="flex size-9 items-center justify-center rounded-lg bg-primary text-primary-foreground">
              <PanelsTopLeft className="size-5" aria-hidden="true" />
            </div>
            <div>
              <p className="text-sm font-semibold">InterHack</p>
              <p className="text-xs text-muted-foreground">Fullstack starter</p>
            </div>
          </div>

          <nav className="hidden items-center gap-2 sm:flex" aria-label="Main navigation">
            <NavLink to="/dashboard" className={navLinkClass}>
              Dashboard
            </NavLink>
          </nav>

          <div className="flex items-center gap-2">
            <Button asChild variant="secondary" size="sm">
              <a href="http://localhost:8000/docs" target="_blank" rel="noreferrer">
                <Database className="size-4" aria-hidden="true" />
                API Docs
              </a>
            </Button>
            <Button asChild size="sm">
              <a href="http://localhost:8000/health" target="_blank" rel="noreferrer">
                <Activity className="size-4" aria-hidden="true" />
                Health
              </a>
            </Button>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-6xl px-4 py-6 sm:px-6">
        <Outlet />
      </main>
    </div>
  );
}

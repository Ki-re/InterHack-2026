import { Database, LogOut, PanelsTopLeft } from "lucide-react";
import { NavLink, Outlet, useNavigate } from "react-router-dom";

import { API_BASE_URL } from "@/api/client";
import { useAuth } from "@/auth/auth-context";
import { Button } from "@/components/ui/button";

const navLinkClass = ({ isActive }: { isActive: boolean }) =>
  [
    "inline-flex h-9 items-center rounded-md px-3 text-sm font-medium transition-colors",
    isActive
      ? "bg-secondary text-secondary-foreground"
      : "text-muted-foreground hover:bg-secondary hover:text-secondary-foreground",
  ].join(" ");

export function AppLayout() {
  const { logout, user } = useAuth();
  const navigate = useNavigate();

  function handleLogout() {
    logout();
    navigate("/", { replace: true });
  }

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
            {user ? (
              <span className="hidden max-w-[220px] truncate text-sm text-muted-foreground md:block">
                {user.email}
              </span>
            ) : null}
            <Button asChild variant="secondary" size="sm">
              <a href={`${API_BASE_URL}/docs`} target="_blank" rel="noreferrer">
                <Database className="size-4" aria-hidden="true" />
                API Docs
              </a>
            </Button>
            <Button variant="outline" size="sm" type="button" onClick={handleLogout}>
              <LogOut className="size-4" aria-hidden="true" />
              Logout
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

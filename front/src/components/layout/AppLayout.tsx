import { LogOut, UserRound, Languages } from "lucide-react";
import { NavLink, Outlet, useNavigate } from "react-router-dom";

import { useAuth } from "@/auth/auth-context";
import { Button } from "@/components/ui/button";
import { useTranslation } from "@/contexts/LanguageContext";
import inibsaLogo from "@/assets/logo.png";

const navLinkClass = ({ isActive }: { isActive: boolean }) =>
  [
    "inline-flex h-9 items-center rounded-md px-3 text-sm font-medium transition-colors",
    isActive
      ? "bg-primary text-primary-foreground"
      : "text-muted-foreground hover:bg-secondary hover:text-secondary-foreground",
  ].join(" ");

export function AppLayout() {
  const { logout, user } = useAuth();
  const { t, language, setLanguage } = useTranslation();
  const navigate = useNavigate();

  function handleLogout() {
    logout();
    navigate("/", { replace: true });
  }

  return (
    <div className="min-h-screen bg-background text-foreground">
      <header className="sticky top-0 z-30 border-b bg-card/95 backdrop-blur">
        <div className="mx-auto flex h-16 max-w-[1440px] items-center justify-between gap-4 px-4 sm:px-6">
          <div className="flex min-w-0 items-center gap-3">
            <img src={inibsaLogo} alt="INIBSA" className="h-8 w-auto shrink-0" />
          </div>

          <div className="flex min-w-0 items-center gap-2">
            <div className="flex items-center gap-1 rounded-md border bg-background p-1">
              <Button
                variant={language === "ca" ? "secondary" : "ghost"}
                size="sm"
                className="h-7 px-2 text-xs"
                onClick={() => setLanguage("ca")}
              >
                CA
              </Button>
              <Button
                variant={language === "es" ? "secondary" : "ghost"}
                size="sm"
                className="h-7 px-2 text-xs"
                onClick={() => setLanguage("es")}
              >
                ES
              </Button>
            </div>

            <div className="hidden min-w-0 items-center gap-2 rounded-md border bg-background px-3 py-2 md:flex">
              <UserRound className="size-4 shrink-0 text-muted-foreground" aria-hidden="true" />
              <span className="max-w-48 truncate text-sm text-muted-foreground">
                {user?.email ?? "delegado@inibsa.local"}
              </span>
            </div>
            <Button variant="outline" size="sm" type="button" onClick={handleLogout}>
              <LogOut className="size-4" aria-hidden="true" />
              {t("app.logout")}
            </Button>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-[1440px] px-4 py-6 sm:px-6">
        <Outlet />
      </main>
    </div>
  );
}

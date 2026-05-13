import { LogOut, ShieldCheck, UserRound } from "lucide-react";
import { Outlet, useNavigate } from "react-router-dom";

import { useAuth } from "@/auth/auth-context";
import { LanguageSwitcher } from "@/components/LanguageSwitcher";
import { Button } from "@/components/ui/button";
import { NotificationBell } from "@/components/NotificationBell";
import { useAgent } from "@/contexts/AgentContext";
import { useDemoMode } from "@/contexts/DemoModeContext";
import { useTranslation } from "@/contexts/LanguageContext";
import inibsaLogo from "@/assets/logo.png";


export function AppLayout() {
  const { logout, user } = useAuth();
  const { t } = useTranslation();
  const { isDemoMode } = useDemoMode();
  const { selectedAgentId } = useAgent();
  const navigate = useNavigate();

  function handleLogout() {
    logout();
    navigate("/login", { replace: true });
  }

  return (
    <div className="min-h-screen bg-background text-foreground">
      <header className="sticky top-0 z-30 border-b bg-card/95 backdrop-blur">
        <div className="mx-auto flex h-16 max-w-[1440px] items-center justify-between gap-4 px-4 sm:px-6">
          <div className="flex min-w-0 items-center gap-3">
            <img src={inibsaLogo} alt="INIBSA" className="h-8 w-auto shrink-0" />
          </div>

          <div className="flex min-w-0 items-center gap-2">
            {user?.role !== "regional_manager" && <NotificationBell agentId={selectedAgentId} />}
            {isDemoMode ? (
              <span className="hidden items-center gap-1 rounded-md border border-green-200 bg-green-50 px-2.5 py-1.5 text-xs font-medium text-green-800 sm:inline-flex">
                <ShieldCheck className="size-3.5" aria-hidden="true" />
                {t("demo.badge")}
              </span>
            ) : null}
            <LanguageSwitcher />

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

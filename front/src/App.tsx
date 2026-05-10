import type { ReactNode } from "react";
import { Navigate, Route, Routes } from "react-router-dom";

import { useAuth } from "@/auth/auth-context";
import { AppLayout } from "@/components/layout/AppLayout";
import { LanguageProvider, useTranslation } from "@/contexts/LanguageContext";
import { Dashboard } from "@/pages/Dashboard";
import { Login } from "@/pages/Login";
import { RegionalDashboard } from "@/pages/RegionalDashboard";

export function App() {
  return (
    <LanguageProvider>
      <Routes>
        <Route
          path="/"
          element={
            <PublicOnlyRoute>
              <Login />
            </PublicOnlyRoute>
          }
        />
        <Route
          element={
            <ProtectedRoute>
              <AppLayout />
            </ProtectedRoute>
          }
        >
          <Route path="/dashboard" element={<Dashboard />} />
          <Route path="/regional-dashboard" element={<RegionalDashboard />} />
        </Route>
        <Route path="*" element={<FallbackRedirect />} />
      </Routes>
    </LanguageProvider>
  );
}

function ProtectedRoute({ children }: { children: ReactNode }) {
  const { isLoading, user } = useAuth();

  if (isLoading) {
    return <AuthLoading />;
  }

  if (!user) {
    return <Navigate to="/" replace />;
  }

  return children;
}

function PublicOnlyRoute({ children }: { children: ReactNode }) {
  const { isLoading, user } = useAuth();

  if (isLoading) {
    return <AuthLoading />;
  }

  if (user) {
    return <Navigate to={getDefaultRoute(user.role)} replace />;
  }

  return children;
}

function FallbackRedirect() {
  const { isLoading, user } = useAuth();

  if (isLoading) {
    return <AuthLoading />;
  }

  return <Navigate to={user ? getDefaultRoute(user.role) : "/"} replace />;
}

function getDefaultRoute(role: string) {
  return role === "regional_manager" ? "/regional-dashboard" : "/dashboard";
}

function AuthLoading() {
  const { t } = useTranslation();
  return (
    <div className="flex min-h-screen items-center justify-center bg-background px-4 text-sm text-muted-foreground">
      {t("login.entering")}
    </div>
  );
}

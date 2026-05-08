import { Navigate, Route, Routes } from "react-router-dom";

import { AppLayout } from "@/layouts/app-layout";
import { DashboardPage } from "@/pages/dashboard-page";

export function App() {
  return (
    <Routes>
      <Route element={<AppLayout />}>
        <Route index element={<DashboardPage />} />
        <Route path="/dashboard" element={<DashboardPage />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Route>
    </Routes>
  );
}

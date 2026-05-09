import { AlertRow } from "@/components/AlertRow";
import { useTranslation } from "@/contexts/LanguageContext";
import type { SalesAlert } from "@/types/alerts";
import { useState } from "react";

type AlertTableProps = {
  alerts: SalesAlert[];
  onAskInsight: (alert: SalesAlert) => void;
  onAttend: (alert: SalesAlert) => void;
};

export function AlertTable({ alerts, onAskInsight, onAttend }: AlertTableProps) {
  const { t } = useTranslation();
  const [expandedAlertId, setExpandedAlertId] = useState<string | null>(null);

  function handleToggleExpanded(alertId: string) {
    setExpandedAlertId((currentId) => (currentId === alertId ? null : alertId));
  }

  return (
    <div className="overflow-hidden rounded-lg border bg-card shadow-sm">
      <div className="flex flex-col gap-2 border-b px-4 py-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h2 className="text-base font-semibold text-foreground">{t("dashboard.table.title")}</h2>
          <p className="mt-1 text-sm text-muted-foreground">
            {t("dashboard.table.description")}
          </p>
        </div>
        <p className="text-sm text-muted-foreground">
          {t("dashboard.table.active_alerts", { count: alerts.length })}
        </p>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full min-w-[1180px] border-collapse text-left">
          <thead className="bg-slate-50">
            <tr className="border-b text-xs font-semibold uppercase tracking-wide text-muted-foreground">
              <th className="px-4 py-3">{t("dashboard.table.cols.client")}</th>
              <th className="px-4 py-3">{t("dashboard.table.cols.risk")}</th>
              <th className="px-4 py-3">{t("dashboard.table.cols.churn_prob")}</th>
              <th className="px-4 py-3">{t("dashboard.table.cols.buy_prop")}</th>
              <th className="px-4 py-3">{t("dashboard.table.cols.value")}</th>
              <th className="px-4 py-3">{t("dashboard.table.cols.explanation")}</th>
              <th className="px-4 py-3">{t("dashboard.table.cols.churn_type")}</th>
              <th className="px-4 py-3">{t("dashboard.table.cols.actions")}</th>
            </tr>
          </thead>
          <tbody>
            {alerts.map((alert) => (
              <AlertRow
                key={alert.id}
                alert={alert}
                isExpanded={expandedAlertId === alert.id}
                onAskInsight={onAskInsight}
                onAttend={onAttend}
                onToggleExpanded={handleToggleExpanded}
              />
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

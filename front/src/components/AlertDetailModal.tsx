import { AlertTriangle, CheckCircle2, X } from "lucide-react";

import { FollowUpForm } from "@/components/FollowUpForm";
import { Button } from "@/components/ui/button";
import { useTranslation } from "@/contexts/LanguageContext";
import type { CustomerValue, InteractionRecord, RiskLevel, SalesAlert } from "@/types/alerts";

type AlertDetailModalProps = {
  alert: SalesAlert | null;
  onClose: () => void;
  onSubmit: (alertId: string, record: InteractionRecord) => void;
};

export function AlertDetailModal({ alert, onClose, onSubmit }: AlertDetailModalProps) {
  const { t } = useTranslation();

  if (!alert) {
    return null;
  }

  const riskLabels: Record<RiskLevel, string> = {
    high: t("risk.high"),
    medium: t("risk.medium"),
    low: t("risk.low"),
  };

  const valueLabels: Record<CustomerValue, string> = {
    high: t("customer_value.high"),
    medium: t("customer_value.medium"),
    low: t("customer_value.low"),
  };

  return (
    <div
      aria-modal="true"
      className="fixed inset-0 z-40 flex items-center justify-center bg-slate-950/35 px-4 py-6"
      role="dialog"
    >
      <div className="max-h-[calc(100vh-3rem)] w-full max-w-2xl overflow-y-auto rounded-lg border bg-card shadow-xl">
        <div className="flex items-start justify-between gap-4 border-b px-5 py-4">
          <div>
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              {alert.status === "attended" ? (
                <CheckCircle2 className="size-4 text-green-600" aria-hidden="true" />
              ) : (
                <AlertTriangle className="size-4 text-red-600" aria-hidden="true" />
              )}
              {t("modal.risk_label", {
                label: riskLabels[alert.riskLevel],
                churn: alert.churnProbability,
              })}
            </div>
            <h2 className="mt-1 text-xl font-semibold text-foreground">{alert.clientName}</h2>
          </div>
          <Button aria-label={t("modal.close")} size="icon" type="button" variant="ghost" onClick={onClose}>
            <X className="size-4" aria-hidden="true" />
          </Button>
        </div>

        <div className="space-y-5 px-5 py-5">
          <div className="grid gap-3 sm:grid-cols-3">
            <Metric label={t("dashboard.table.cols.churn_prob")} value={`${alert.churnProbability}%`} />
            <Metric label={t("dashboard.table.cols.buy_prop")} value={`${alert.purchasePropensity}%`} />
            <Metric label={t("dashboard.table.cols.value")} value={valueLabels[alert.customerValue]} />
          </div>

          <div className="rounded-md border bg-background px-4 py-3">
            <p className="text-sm font-medium text-foreground">{t("modal.explanation")}</p>
            <p className="mt-1 text-sm leading-6 text-muted-foreground">{alert.explanation}</p>
          </div>

          <FollowUpForm
            onCancel={onClose}
            onSubmit={(record) => onSubmit(alert.id, record)}
          />
        </div>
      </div>
    </div>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-md border bg-background px-4 py-3">
      <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">{label}</p>
      <p className="mt-1 text-lg font-semibold capitalize text-foreground">{value}</p>
    </div>
  );
}

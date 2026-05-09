import { CheckCircle2, ChevronDown, ChevronRight, ClipboardCheck, MessageSquareText } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";

import { Button } from "@/components/ui/button";
import { useTranslation } from "@/contexts/LanguageContext";
import { cn } from "@/lib/utils";
import type { CustomerValue, RiskLevel, SalesAlert } from "@/types/alerts";

type AlertRowProps = {
  alert: SalesAlert;
  isExpanded: boolean;
  onAskInsight: (alert: SalesAlert) => void;
  onAttend: (alert: SalesAlert) => void;
  onToggleExpanded: (alertId: string) => void;
};

export function AlertRow({
  alert,
  isExpanded,
  onAskInsight,
  onAttend,
  onToggleExpanded,
}: AlertRowProps) {
  const { t } = useTranslation();
  const isAttended = alert.status === "attended";

  const riskConfig: Record<
    RiskLevel,
    {
      label: string;
      className: string;
      dotClassName: string;
    }
  > = {
    high: {
      label: t("risk.high"),
      className: "border-red-200 bg-red-50 text-red-700",
      dotClassName: "bg-red-500",
    },
    medium: {
      label: t("risk.medium"),
      className: "border-amber-200 bg-amber-50 text-amber-700",
      dotClassName: "bg-amber-500",
    },
    low: {
      label: t("risk.low"),
      className: "border-green-200 bg-green-50 text-green-700",
      dotClassName: "bg-green-500",
    },
  };

  const churnTypeLabel = alert.churnType === "total" ? t("churn_type.total") : alert.churnType;

  const valueLabels: Record<CustomerValue, string> = {
    high: t("customer_value.high"),
    medium: t("customer_value.medium"),
    low: t("customer_value.low"),
  };

  const risk = riskConfig[alert.riskLevel];

  return (
    <>
      <tr className={cn("border-b bg-card transition-colors hover:bg-muted/40", isAttended && "bg-muted/35")}>
        <td className="min-w-56 px-4 py-4 align-top">
          <div className="flex items-start gap-3">
            <button
              aria-label={isExpanded ? t("dashboard.table.row.hide_explanation") : t("dashboard.table.row.show_explanation")}
              className="mt-0.5 flex size-7 items-center justify-center rounded-md text-muted-foreground transition-colors hover:bg-secondary hover:text-foreground"
              type="button"
              onClick={() => onToggleExpanded(alert.id)}
            >
              {isExpanded ? (
                <ChevronDown className="size-4" aria-hidden="true" />
              ) : (
                <ChevronRight className="size-4" aria-hidden="true" />
              )}
            </button>
            <div>
              <p className="font-medium text-foreground">{alert.clientName}</p>
              <p className="mt-1 text-xs text-muted-foreground">
                {isAttended ? t("dashboard.table.row.attended") : t("dashboard.table.row.pending")} · ID {alert.id.replace("alert-", "")}
              </p>
            </div>
          </div>
        </td>

        <td className="px-4 py-4 align-top">
          <span
            className={cn(
              "inline-flex items-center gap-2 rounded-full border px-2.5 py-1 text-xs font-medium",
              risk.className,
            )}
          >
            <span className={cn("size-2 rounded-full", risk.dotClassName)} aria-hidden="true" />
            {risk.label}
          </span>
        </td>

        <td className="min-w-28 px-4 py-4 align-top">
          <PercentBadge value={alert.churnProbability} tone="risk" />
        </td>

        <td className="min-w-28 px-4 py-4 align-top">
          <PercentBadge value={alert.purchasePropensity} tone="opportunity" />
        </td>

        <td className="px-4 py-4 align-top">
          <span className="inline-flex rounded-full border bg-background px-2.5 py-1 text-xs font-medium text-foreground">
            {valueLabels[alert.customerValue]}
          </span>
        </td>

        <td className="min-w-72 max-w-md px-4 py-4 align-top">
          <p className="line-clamp-2 text-sm leading-6 text-muted-foreground">{alert.explanation}</p>
          <button
            className="mt-1 text-xs font-medium text-primary hover:underline"
            type="button"
            onClick={() => onToggleExpanded(alert.id)}
          >
            {isExpanded ? t("dashboard.table.row.hide_detail") : t("dashboard.table.row.show_detail")}
          </button>
        </td>

        <td className="w-28 px-4 py-4 align-top">
          <span className="inline-block max-w-full rounded-md bg-secondary px-2.5 py-1 text-xs font-medium leading-5 text-secondary-foreground break-words">
            {churnTypeLabel}
          </span>
        </td>

        <td className="min-w-48 px-4 py-4 align-top">
          <div className="flex flex-col gap-2">
            <Button size="sm" type="button" variant="outline" className="w-full" onClick={() => onAskInsight(alert)}>
              <MessageSquareText className="size-4" aria-hidden="true" />
              {t("dashboard.table.row.ask_ai")}
            </Button>
            <Button
              disabled={isAttended}
              size="sm"
              type="button"
              variant={isAttended ? "secondary" : "default"}
              className="w-full"
              onClick={() => onAttend(alert)}
            >
              {isAttended ? (
                <CheckCircle2 className="size-4" aria-hidden="true" />
              ) : (
                <ClipboardCheck className="size-4" aria-hidden="true" />
              )}
              {isAttended ? t("dashboard.table.row.attended") : t("dashboard.table.row.mark_attended")}
            </Button>
          </div>
        </td>
      </tr>

      <AnimatePresence initial={false}>
        {isExpanded && (
          <motion.tr
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: "auto" }}
            exit={{ opacity: 0, height: 0 }}
            className="overflow-hidden border-b bg-muted/25"
          >
            <td className="p-0" colSpan={8}>
              <motion.div
                initial={{ opacity: 0, y: -10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -10 }}
                className="px-4 py-4"
              >
                <div className="grid gap-4 lg:grid-cols-[1fr_280px]">
                  <div>
                    <p className="text-sm font-medium text-foreground">{t("dashboard.table.row.full_explanation")}</p>
                    <p className="mt-1 text-sm leading-6 text-muted-foreground">{alert.explanation}</p>
                  </div>
                  <div className="rounded-md border bg-card px-4 py-3">
                    <p className="text-sm font-medium text-foreground">{t("dashboard.table.row.status_mgmt")}</p>
                    {alert.followUp ? (
                      <p className="mt-1 text-sm leading-6 text-muted-foreground">
                        {t("dashboard.table.row.mgmt_result", {
                          result: alert.followUp.result,
                          channel: alert.followUp.handledBy,
                        })}
                        {alert.followUp.reminder ? ` Reminder: ${alert.followUp.reminder}` : ""}
                      </p>
                    ) : (
                      <p className="mt-1 text-sm text-muted-foreground">{t("dashboard.table.row.no_mgmt")}</p>
                    )}
                  </div>
                </div>
              </motion.div>
            </td>
          </motion.tr>
        )}
      </AnimatePresence>
    </>
  );
}

function PercentBadge({ value, tone }: { value: number; tone: "risk" | "opportunity" }) {
  const level = value >= 67 ? "high" : value >= 34 ? "medium" : "low";

  const className = {
    risk: {
      high: "bg-red-50 border-red-200 text-red-700",
      medium: "bg-amber-50 border-amber-200 text-amber-700",
      low: "bg-green-50 border-green-200 text-green-700",
    },
    opportunity: {
      high: "bg-green-50 border-green-200 text-green-700",
      medium: "bg-amber-50 border-amber-200 text-amber-700",
      low: "bg-red-50 border-red-200 text-red-700",
    },
  }[tone][level];

  return (
    <span className={cn("inline-flex items-center rounded-full border px-2.5 py-1 text-sm font-semibold tabular-nums", className)}>
      {value}%
    </span>
  );
}

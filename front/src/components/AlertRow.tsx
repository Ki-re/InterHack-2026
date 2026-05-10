import { CheckCircle2, ChevronDown, ChevronRight, ClipboardCheck, MessageSquareText, Phone, Mail, MapPin, HelpCircle, Trash2, RotateCcw, XCircle } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";

import { Button } from "@/components/ui/button";
import { useTranslation } from "@/contexts/LanguageContext";
import { cn } from "@/lib/utils";
import type { CustomerValue, InteractionRecord, RiskLevel, SalesAlert, SystemEventRecord } from "@/types/alerts";

type AlertRowProps = {
  alert: SalesAlert;
  isExpanded: boolean;
  onAskInsight: (alert: SalesAlert) => void;
  onAttend: (alert: SalesAlert) => void;
  onOpenDismiss: (alert: SalesAlert) => void;
  onRecover: (alertId: string) => void;
  onToggleExpanded: (alertId: string) => void;
};

export function AlertRow({
  alert,
  isExpanded,
  onAskInsight,
  onAttend,
  onOpenDismiss,
  onRecover,
  onToggleExpanded,
}: AlertRowProps) {
  const { t } = useTranslation();

  const isAttended = alert.status === "attended";
  const isDismissed = alert.status === "dismissed";
  const isActionable = !isAttended && !isDismissed;

  const riskConfig: Record<RiskLevel, { label: string; className: string; dotClassName: string }> = {
    high: { label: t("risk.high"), className: "border-red-200 bg-red-50 text-red-700", dotClassName: "bg-red-500" },
    medium: { label: t("risk.medium"), className: "border-amber-200 bg-amber-50 text-amber-700", dotClassName: "bg-amber-500" },
    low: { label: t("risk.low"), className: "border-green-200 bg-green-50 text-green-700", dotClassName: "bg-green-500" },
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
      <tr className={cn("border-b bg-card transition-colors hover:bg-muted/40", (isAttended || isDismissed) && "bg-muted/35")}>
        <td className="min-w-56 px-4 py-4 align-top">
          <div className="flex items-start gap-3">
            <button
              aria-label={isExpanded ? t("dashboard.table.row.hide_explanation") : t("dashboard.table.row.show_explanation")}
              className="mt-0.5 flex size-7 items-center justify-center rounded-md text-muted-foreground transition-colors hover:bg-secondary hover:text-foreground"
              type="button"
              onClick={() => onToggleExpanded(alert.id)}
            >
              {isExpanded ? <ChevronDown className="size-4" /> : <ChevronRight className="size-4" />}
            </button>
            <div>
              <p className="font-medium text-foreground">{alert.clientName}</p>
              <p className="mt-1 text-xs text-muted-foreground">
                {isDismissed
                  ? t("dashboard.table.row.dismissed")
                  : isAttended
                  ? t("dashboard.table.row.attended")
                  : t("dashboard.table.row.pending")}
                {" · ID "}{alert.id.replace("alert-", "")}
              </p>
            </div>
          </div>
        </td>

        <td className="px-4 py-4 align-top">
          <span className={cn("inline-flex items-center gap-2 rounded-full border px-2.5 py-1 text-xs font-medium", risk.className)}>
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
            {isDismissed ? (
              <Button
                size="sm"
                type="button"
                variant="outline"
                className="w-full"
                onClick={() => onRecover(alert.id)}
              >
                <RotateCcw className="size-4" aria-hidden="true" />
                {t("dismiss.recover")}
              </Button>
            ) : (
              <>
                <Button
                  disabled={!isActionable}
                  size="sm"
                  type="button"
                  variant={isAttended ? "secondary" : "default"}
                  className="w-full"
                  onClick={() => isActionable && onAttend(alert)}
                >
                  {isAttended ? (
                    <CheckCircle2 className="size-4" aria-hidden="true" />
                  ) : (
                    <ClipboardCheck className="size-4" aria-hidden="true" />
                  )}
                  {isAttended ? t("dashboard.table.row.attended") : t("dashboard.table.row.mark_attended")}
                </Button>
                <Button
                  disabled={!isActionable}
                  size="sm"
                  type="button"
                  variant="outline"
                  className="w-full text-destructive hover:bg-destructive/10 hover:text-destructive disabled:opacity-40"
                  onClick={() => isActionable && onOpenDismiss(alert)}
                >
                  <Trash2 className="size-4" aria-hidden="true" />
                  {t("dismiss.button")}
                </Button>
              </>
            )}
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
                <div className="grid gap-4 lg:grid-cols-[1fr_320px]">
                  <div>
                    <p className="text-sm font-medium text-foreground">{t("dashboard.table.row.full_explanation")}</p>
                    <p className="mt-1 text-sm leading-6 text-muted-foreground">{alert.explanation}</p>
                    {isDismissed && alert.dismissReason && (
                      <div className="mt-3 rounded-md border border-destructive/20 bg-destructive/5 px-3 py-2">
                        <p className="text-xs font-medium text-destructive">{t("dismiss.title")}</p>
                        <p className="mt-0.5 text-xs text-muted-foreground">{alert.dismissReason}</p>
                      </div>
                    )}
                  </div>
                  <Changelog interactions={alert.interactions} events={alert.events} />
                </div>
              </motion.div>
            </td>
          </motion.tr>
        )}
      </AnimatePresence>
    </>
  );
}

function Changelog({ interactions, events }: { interactions: InteractionRecord[]; events: SystemEventRecord[] }) {
  const { t } = useTranslation();

  const channelIcon: Record<string, React.ReactNode> = {
    phone: <Phone className="size-3.5" />,
    visit: <MapPin className="size-3.5" />,
    email: <Mail className="size-3.5" />,
    other: <HelpCircle className="size-3.5" />,
  };

  const channelLabel: Record<string, string> = {
    phone: t("changelog.phone"),
    visit: t("changelog.visit"),
    email: t("changelog.email"),
    other: t("changelog.other"),
  };

  const resultLabel: Record<string, string> = {
    positive: t("changelog.result_positive"),
    neutral: t("changelog.result_neutral"),
    negative: t("changelog.result_negative"),
  };

  function getOutcomeLabel(rec: InteractionRecord): string {
    if (rec.handledBy === "phone") return rec.answered ? t("changelog.answered") : t("changelog.not_answered");
    if (rec.handledBy === "visit") return rec.visitSuccessful ? t("changelog.visit_ok") : t("changelog.visit_fail");
    if (rec.handledBy === "email") return rec.emailResponseReceived ? t("changelog.email_received") : t("changelog.email_no_response");
    return "";
  }

  function getOutcomeColor(rec: InteractionRecord): string {
    const success =
      rec.handledBy === "phone" ? rec.answered :
      rec.handledBy === "visit" ? rec.visitSuccessful :
      rec.handledBy === "email" ? rec.emailResponseReceived :
      true;
    return success ? "text-green-700 bg-green-50 border-green-200" : "text-amber-700 bg-amber-50 border-amber-200";
  }

  // Merge interactions and system events into a single sorted timeline
  type TimelineEntry =
    | { kind: "interaction"; ts: string; data: InteractionRecord }
    | { kind: "event"; ts: string; data: SystemEventRecord };

  const timeline: TimelineEntry[] = [
    ...interactions.map((d) => ({ kind: "interaction" as const, ts: d.submittedAt, data: d })),
    ...events.map((d) => ({ kind: "event" as const, ts: d.timestamp, data: d })),
  ].sort((a, b) => b.ts.localeCompare(a.ts)); // newest first

  const eventConfig: Record<string, { icon: React.ReactNode; label: string; className: string }> = {
    closed: {
      icon: <CheckCircle2 className="size-3.5" />,
      label: t("changelog.event_closed"),
      className: "text-green-700 bg-green-50 border-green-200",
    },
    dismissed: {
      icon: <XCircle className="size-3.5" />,
      label: t("changelog.event_dismissed"),
      className: "text-red-700 bg-red-50 border-red-200",
    },
    reopened: {
      icon: <RotateCcw className="size-3.5" />,
      label: t("changelog.event_reopened"),
      className: "text-blue-700 bg-blue-50 border-blue-200",
    },
  };

  return (
    <div className="rounded-md border bg-card px-4 py-3">
      <p className="text-sm font-medium text-foreground">{t("changelog.title")}</p>
      {timeline.length === 0 ? (
        <p className="mt-2 text-sm text-muted-foreground">{t("changelog.empty")}</p>
      ) : (
        <ol className="mt-3 space-y-3">
          {timeline.map((entry) => {
            if (entry.kind === "event") {
              const cfg = eventConfig[entry.data.type];
              return (
                <li key={entry.data.id} className="flex gap-3 text-sm">
                  <span className={cn("mt-0.5 flex size-6 shrink-0 items-center justify-center rounded-full border", cfg.className)}>
                    {cfg.icon}
                  </span>
                  <div className="min-w-0 flex-1">
                    <div className="flex flex-wrap items-center gap-1.5">
                      <span className="font-medium text-foreground">{cfg.label}</span>
                      <span className="ml-auto text-xs text-muted-foreground">
                        {new Date(entry.data.timestamp).toLocaleDateString()}
                      </span>
                    </div>
                    {entry.data.reason && (
                      <p className="mt-1 text-xs text-muted-foreground">{entry.data.reason}</p>
                    )}
                  </div>
                </li>
              );
            }

            const rec = entry.data;
            return (
              <li key={rec.id} className="flex gap-3 text-sm">
                <span className="mt-0.5 flex size-6 shrink-0 items-center justify-center rounded-full border bg-background text-muted-foreground">
                  {channelIcon[rec.handledBy]}
                </span>
                <div className="min-w-0 flex-1">
                  <div className="flex flex-wrap items-center gap-1.5">
                    <span className="font-medium text-foreground">{channelLabel[rec.handledBy]}</span>
                    {rec.handledBy !== "other" && (
                      <span className={cn("inline-flex rounded-full border px-2 py-0.5 text-xs font-medium", getOutcomeColor(rec))}>
                        {getOutcomeLabel(rec)}
                      </span>
                    )}
                    {rec.result && (
                      <span className="inline-flex rounded-full border border-slate-200 bg-slate-50 px-2 py-0.5 text-xs text-slate-600">
                        {resultLabel[rec.result]}
                      </span>
                    )}
                    <span className="ml-auto text-xs text-muted-foreground">
                      {new Date(rec.submittedAt).toLocaleDateString()}
                    </span>
                  </div>
                  {rec.notes && (
                    <p className="mt-1 text-xs text-muted-foreground">{rec.notes}</p>
                  )}
                </div>
              </li>
            );
          })}
        </ol>
      )}
    </div>
  );
}

function PercentBadge({ value, tone }: { value: number; tone: "risk" | "opportunity" }) {
  const level = value >= 67 ? "high" : value >= 34 ? "medium" : "low";
  const className = {
    risk: { high: "bg-red-50 border-red-200 text-red-700", medium: "bg-amber-50 border-amber-200 text-amber-700", low: "bg-green-50 border-green-200 text-green-700" },
    opportunity: { high: "bg-green-50 border-green-200 text-green-700", medium: "bg-amber-50 border-amber-200 text-amber-700", low: "bg-red-50 border-red-200 text-red-700" },
  }[tone][level];

  return (
    <span className={cn("inline-flex items-center rounded-full border px-2.5 py-1 text-sm font-semibold tabular-nums", className)}>
      {value}%
    </span>
  );
}

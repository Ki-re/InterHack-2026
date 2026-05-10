import { useMemo, useState, type ReactNode } from "react";
import { AlertTriangle, CheckCircle2, TrendingUp, Users } from "lucide-react";
import { motion } from "framer-motion";

import { AIInsightPanel } from "@/components/AIInsightPanel";
import { AlertDetailModal } from "@/components/AlertDetailModal";
import { AlertTable } from "@/components/AlertTable";
import { DismissModal } from "@/components/DismissModal";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useTranslation } from "@/contexts/LanguageContext";
import { mockAlerts } from "@/data/mock-alerts";
import type { AlertStatus, InteractionRecord, SalesAlert, SystemEventRecord } from "@/types/alerts";

const containerVariants = {
  hidden: { opacity: 0 },
  show: { opacity: 1, transition: { staggerChildren: 0.05 } },
};

const itemVariants = {
  hidden: { opacity: 0, y: 10 },
  show: { opacity: 1, y: 0 },
};

export function Dashboard() {
  const { t } = useTranslation();
  const [alerts, setAlerts] = useState<SalesAlert[]>(mockAlerts);
  const [activeTab, setActiveTab] = useState<AlertStatus>("pending");
  const [selectedAlert, setSelectedAlert] = useState<SalesAlert | null>(null);
  const [dismissTarget, setDismissTarget] = useState<SalesAlert | null>(null);
  const [insightAlert, setInsightAlert] = useState<SalesAlert | null>(null);

  const metrics = useMemo(() => {
    const pending = alerts.filter((a) => a.status === "pending").length;
    const highRisk = alerts.filter((a) => a.riskLevel === "high").length;
    const attended = alerts.filter((a) => a.status === "attended").length;
    const dismissed = alerts.filter((a) => a.status === "dismissed").length;
    const averageChurn = Math.round(
      alerts.reduce((total, a) => total + a.churnProbability, 0) / Math.max(alerts.length, 1),
    );
    return { pending, highRisk, attended, dismissed, averageChurn };
  }, [alerts]);

  const filteredAlerts = useMemo(
    () => alerts.filter((a) => a.status === activeTab),
    [alerts, activeTab],
  );

  function handleSubmitInteraction(alertId: string, record: InteractionRecord) {
    setAlerts((prev) =>
      prev.map((a) => {
        if (a.id !== alertId) return a;
        const closedEvent: SystemEventRecord | null = !record.keepOpen
          ? { id: `evt-${alertId}-${Date.now()}`, type: "closed", timestamp: new Date().toISOString() }
          : null;
        return {
          ...a,
          status: record.keepOpen ? "pending" : "attended",
          interactions: [...a.interactions, record],
          events: closedEvent ? [...a.events, closedEvent] : a.events,
        };
      }),
    );
    setSelectedAlert(null);
  }

  function handleDismiss(alertId: string, reason?: string) {
    setAlerts((prev) =>
      prev.map((a) => {
        if (a.id !== alertId) return a;
        const evt: SystemEventRecord = {
          id: `evt-${alertId}-${Date.now()}`,
          type: "dismissed",
          reason,
          timestamp: new Date().toISOString(),
        };
        return {
          ...a,
          status: "dismissed",
          dismissReason: reason,
          dismissedAt: new Date().toISOString(),
          events: [...a.events, evt],
        };
      }),
    );
  }

  function handleRecover(alertId: string) {
    setAlerts((prev) =>
      prev.map((a) => {
        if (a.id !== alertId) return a;
        const evt: SystemEventRecord = {
          id: `evt-${alertId}-${Date.now()}`,
          type: "reopened",
          timestamp: new Date().toISOString(),
        };
        return {
          ...a,
          status: "pending",
          dismissReason: undefined,
          dismissedAt: undefined,
          events: [...a.events, evt],
        };
      }),
    );
  }

  const liveSelectedAlert = selectedAlert
    ? alerts.find((a) => a.id === selectedAlert.id) ?? selectedAlert
    : null;
  const liveInsightAlert = insightAlert
    ? alerts.find((a) => a.id === insightAlert.id) ?? insightAlert
    : null;

  const tabs: Array<{ key: AlertStatus; label: string; count: number }> = [
    { key: "pending", label: t("dashboard.metrics.pending"), count: metrics.pending },
    { key: "attended", label: t("dashboard.metrics.attended"), count: metrics.attended },
    { key: "dismissed", label: t("dashboard.metrics.dismissed"), count: metrics.dismissed },
  ];

  return (
    <motion.div variants={containerVariants} initial="hidden" animate="show" className="space-y-6">
      <motion.section
        variants={itemVariants}
        className="flex flex-col gap-4 border-b pb-5 lg:flex-row lg:items-end lg:justify-between"
      >
        <div className="max-w-3xl">
          <h1 className="text-3xl font-semibold tracking-normal text-foreground">
            {t("dashboard.title")}
          </h1>
          <p className="mt-2 text-sm leading-6 text-muted-foreground">{t("dashboard.subtitle")}</p>
        </div>
        <div className="rounded-md border bg-card px-4 py-3 text-sm text-muted-foreground shadow-sm">
          {t("dashboard.mock_data")}
        </div>
      </motion.section>

      <motion.section variants={itemVariants} className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <MetricCard
          icon={<AlertTriangle className="size-5 text-red-600" />}
          label={t("dashboard.metrics.pending")}
          value={String(metrics.pending)}
          description={t("dashboard.metrics.pending_desc")}
        />
        <MetricCard
          icon={<TrendingUp className="size-5 text-red-600" />}
          label={t("dashboard.metrics.high_risk")}
          value={String(metrics.highRisk)}
          description={t("dashboard.metrics.high_risk_desc")}
        />
        <MetricCard
          icon={<Users className="size-5 text-primary" />}
          label={t("dashboard.metrics.avg_churn")}
          value={`${metrics.averageChurn}%`}
          description={t("dashboard.metrics.avg_churn_desc")}
        />
        <MetricCard
          icon={<CheckCircle2 className="size-5 text-green-600" />}
          label={t("dashboard.metrics.attended")}
          value={String(metrics.attended)}
          description={t("dashboard.metrics.attended_desc")}
        />
      </motion.section>

      <motion.div variants={itemVariants} className="space-y-3">
        <div className="flex gap-2" role="tablist">
          {tabs.map((tab) => (
            <button
              key={tab.key}
              role="tab"
              aria-selected={activeTab === tab.key}
              type="button"
              onClick={() => setActiveTab(tab.key)}
              className={[
                "inline-flex items-center gap-2 rounded-md border px-4 py-2 text-sm font-medium transition-colors",
                activeTab === tab.key
                  ? "border-primary bg-primary text-primary-foreground"
                  : "border-border bg-card text-muted-foreground hover:bg-secondary hover:text-foreground",
              ].join(" ")}
            >
              {tab.label}
              <span
                className={[
                  "inline-flex size-5 items-center justify-center rounded-full text-xs font-semibold",
                  activeTab === tab.key
                    ? "bg-primary-foreground/20 text-primary-foreground"
                    : "bg-secondary text-secondary-foreground",
                ].join(" ")}
              >
                {tab.count}
              </span>
            </button>
          ))}
        </div>

        <AlertTable
          alerts={filteredAlerts}
          onAskInsight={setInsightAlert}
          onAttend={setSelectedAlert}
          onOpenDismiss={setDismissTarget}
          onRecover={handleRecover}
        />
      </motion.div>

      <AlertDetailModal
        alert={liveSelectedAlert}
        onClose={() => setSelectedAlert(null)}
        onSubmit={handleSubmitInteraction}
      />
      <DismissModal
        alert={dismissTarget}
        onClose={() => setDismissTarget(null)}
        onConfirm={handleDismiss}
      />
      <AIInsightPanel alert={liveInsightAlert} onClose={() => setInsightAlert(null)} />
    </motion.div>
  );
}

function MetricCard({
  description,
  icon,
  label,
  value,
}: {
  description: string;
  icon: ReactNode;
  label: string;
  value: string;
}) {
  return (
    <Card className="rounded-lg transition-all duration-300 hover:shadow-md">
      <CardHeader className="flex flex-row items-start justify-between gap-3 space-y-0 pb-3">
        <div>
          <p className="text-sm font-medium text-muted-foreground">{label}</p>
          <CardTitle className="mt-1 text-2xl font-semibold">{value}</CardTitle>
        </div>
        <div className="flex size-10 items-center justify-center rounded-md bg-secondary">{icon}</div>
      </CardHeader>
      <CardContent>
        <p className="text-sm text-muted-foreground">{description}</p>
      </CardContent>
    </Card>
  );
}

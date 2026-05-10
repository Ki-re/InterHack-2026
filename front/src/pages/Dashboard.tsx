import { useEffect, useMemo, useState, type ReactNode } from "react";
import { AlertTriangle, CheckCircle2, Loader2, TrendingUp, Users } from "lucide-react";
import { motion } from "framer-motion";

import { AIInsightPanel } from "@/components/AIInsightPanel";
import { AlertDetailModal } from "@/components/AlertDetailModal";
import { AlertTable } from "@/components/AlertTable";
import { DismissModal } from "@/components/DismissModal";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useTranslation } from "@/contexts/LanguageContext";
import { useAgents } from "@/hooks/useAgents";
import { useAlerts } from "@/hooks/useAlerts";
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
  const { data: agents, isLoading: agentsLoading } = useAgents();

  // Auto-select the first agent once agents load
  const [selectedAgentId, setSelectedAgentId] = useState<number | undefined>(undefined);
  useEffect(() => {
    if (agents && agents.length > 0 && selectedAgentId === undefined) {
      setSelectedAgentId(agents[0].id);
    }
  }, [agents, selectedAgentId]);

  const { data: fetchedAlerts, isLoading: alertsLoading } = useAlerts(selectedAgentId);
  const isLoading = agentsLoading || alertsLoading;

  const [alerts, setAlerts] = useState<SalesAlert[]>([]);
  const [activeTab, setActiveTab] = useState<AlertStatus>("pending");
  const [selectedAlert, setSelectedAlert] = useState<SalesAlert | null>(null);
  const [dismissTarget, setDismissTarget] = useState<SalesAlert | null>(null);
  const [insightAlert, setInsightAlert] = useState<SalesAlert | null>(null);

  // Reset alerts when agent changes, then seed from API
  useEffect(() => {
    setAlerts([]);
    setActiveTab("pending");
  }, [selectedAgentId]);

  useEffect(() => {
    if (fetchedAlerts && fetchedAlerts.length > 0) {
      setAlerts(fetchedAlerts);
    }
  }, [fetchedAlerts]);

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

  const zoneLabel = (zone: string) =>
    t(`dashboard.zone_${zone}`) !== `dashboard.zone_${zone}` ? t(`dashboard.zone_${zone}`) : zone;

  const selectedAgent = agents?.find((a) => a.id === selectedAgentId);

  return (
    <motion.div variants={containerVariants} initial="hidden" animate="show" className="space-y-6">

      {/* Delegate selector bar */}
      <motion.div variants={itemVariants} className="flex items-center gap-3 rounded-lg border bg-card px-4 py-3">
        <span className="text-sm font-medium text-muted-foreground whitespace-nowrap">
          {t("dashboard.delegate_label")}:
        </span>
        {agentsLoading ? (
          <span className="flex items-center gap-1.5 text-sm text-muted-foreground">
            <Loader2 className="size-3.5 animate-spin" />
            {t("dashboard.loading_agents")}
          </span>
        ) : (
          <select
            value={selectedAgentId ?? ""}
            onChange={(e) => setSelectedAgentId(Number(e.target.value))}
            className="flex-1 max-w-xs rounded-md border border-border bg-background px-3 py-1.5 text-sm font-medium shadow-sm focus:outline-none focus:ring-2 focus:ring-primary/40"
          >
            {(agents ?? []).map((agent) => (
              <option key={agent.id} value={agent.id}>
                {agent.name} · {zoneLabel(agent.zone)}
              </option>
            ))}
          </select>
        )}
        {selectedAgent && (
          <span className="ml-auto text-xs text-muted-foreground">
            {selectedAgent.email}
          </span>
        )}
      </motion.div>

      {alertsLoading && (
        <div className="flex items-center justify-center py-16 text-muted-foreground gap-2">
          <Loader2 className="size-5 animate-spin" />
          <span className="text-sm">{t("dashboard.loading") ?? "Carregant alertes..."}</span>
        </div>
      )}


      {!alertsLoading && (
      <>
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
      </>
      )}

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

import { useMemo, useState, type ReactNode } from "react";
import { AlertTriangle, CheckCircle2, TrendingUp, Users } from "lucide-react";
import { motion } from "framer-motion";

import { AIInsightPanel } from "@/components/AIInsightPanel";
import { AlertDetailModal } from "@/components/AlertDetailModal";
import { AlertTable } from "@/components/AlertTable";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useTranslation } from "@/contexts/LanguageContext";
import { mockAlerts } from "@/data/mock-alerts";
import type { FollowUpRecord, SalesAlert } from "@/types/alerts";

const containerVariants = {
  hidden: { opacity: 0 },
  show: {
    opacity: 1,
    transition: {
      staggerChildren: 0.05,
    },
  },
};

const itemVariants = {
  hidden: { opacity: 0, y: 10 },
  show: { opacity: 1, y: 0 },
};

export function Dashboard() {
  const { t } = useTranslation();
  const [alerts, setAlerts] = useState<SalesAlert[]>(mockAlerts);
  const [selectedAlert, setSelectedAlert] = useState<SalesAlert | null>(null);
  const [insightAlert, setInsightAlert] = useState<SalesAlert | null>(null);

  const metrics = useMemo(() => {
    const pendingAlerts = alerts.filter((alert) => alert.status === "pending");
    const highRiskAlerts = alerts.filter((alert) => alert.riskLevel === "high");
    const attendedAlerts = alerts.filter((alert) => alert.status === "attended");
    const averageChurn =
      alerts.reduce((total, alert) => total + alert.churnProbability, 0) / Math.max(alerts.length, 1);

    return {
      pending: pendingAlerts.length,
      highRisk: highRiskAlerts.length,
      attended: attendedAlerts.length,
      averageChurn: Math.round(averageChurn),
    };
  }, [alerts]);

  function handleSubmitFollowUp(alertId: string, record: FollowUpRecord) {
    setAlerts((currentAlerts) =>
      currentAlerts.map((alert) =>
        alert.id === alertId
          ? {
              ...alert,
              status: "attended",
              followUp: record,
            }
          : alert,
      ),
    );
    setSelectedAlert(null);
  }

  const liveSelectedAlert = selectedAlert
    ? alerts.find((alert) => alert.id === selectedAlert.id) ?? selectedAlert
    : null;
  const liveInsightAlert = insightAlert
    ? alerts.find((alert) => alert.id === insightAlert.id) ?? insightAlert
    : null;

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
          icon={<AlertTriangle className="size-5 text-red-600" aria-hidden="true" />}
          label={t("dashboard.metrics.pending")}
          value={String(metrics.pending)}
          description={t("dashboard.metrics.pending_desc")}
        />
        <MetricCard
          icon={<TrendingUp className="size-5 text-red-600" aria-hidden="true" />}
          label={t("dashboard.metrics.high_risk")}
          value={String(metrics.highRisk)}
          description={t("dashboard.metrics.high_risk_desc")}
        />
        <MetricCard
          icon={<Users className="size-5 text-primary" aria-hidden="true" />}
          label={t("dashboard.metrics.avg_churn")}
          value={`${metrics.averageChurn}%`}
          description={t("dashboard.metrics.avg_churn_desc")}
        />
        <MetricCard
          icon={<CheckCircle2 className="size-5 text-green-600" aria-hidden="true" />}
          label={t("dashboard.metrics.attended")}
          value={String(metrics.attended)}
          description={t("dashboard.metrics.attended_desc")}
        />
      </motion.section>

      <motion.div variants={itemVariants}>
        <AlertTable alerts={alerts} onAskInsight={setInsightAlert} onAttend={setSelectedAlert} />
      </motion.div>

      <AlertDetailModal
        alert={liveSelectedAlert}
        onClose={() => setSelectedAlert(null)}
        onSubmit={handleSubmitFollowUp}
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

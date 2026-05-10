import { AlertTriangle, CheckCircle2, Clock3, Gauge, TimerReset } from "lucide-react";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { cn } from "@/lib/utils";
import type { ExecutionKpis } from "@/types/regional-dashboard";

type RegionalKpiCardsProps = {
  kpis: ExecutionKpis;
  t: (path: string, params?: Record<string, string | number>) => string;
};

export function RegionalKpiCards({ kpis, t }: RegionalKpiCardsProps) {
  const cards = [
    {
      label: t("regional_dashboard.kpis.execution_score"),
      value: `${kpis.executionScore}`,
      description: t(`regional_dashboard.status.${kpis.status}`),
      icon: <Gauge className="size-4 text-primary" aria-hidden="true" />,
      tone: kpis.status,
    },
    {
      label: t("regional_dashboard.kpis.pending"),
      value: String(kpis.pendingAlerts),
      description: t("regional_dashboard.kpis.pending_desc"),
      icon: <AlertTriangle className="size-4 text-amber-600" aria-hidden="true" />,
      tone: "warning",
    },
    {
      label: t("regional_dashboard.kpis.attended_rate"),
      value: `${kpis.attendedRate}%`,
      description: t("regional_dashboard.kpis.attended_desc"),
      icon: <CheckCircle2 className="size-4 text-green-600" aria-hidden="true" />,
      tone: "good",
    },
    {
      label: t("regional_dashboard.kpis.overdue"),
      value: String(kpis.overdueFollowups),
      description: t("regional_dashboard.kpis.overdue_desc"),
      icon: <TimerReset className="size-4 text-red-600" aria-hidden="true" />,
      tone: "critical",
    },
    {
      label: t("regional_dashboard.kpis.response_time"),
      value: kpis.averageResponseHours === null ? "-" : `${kpis.averageResponseHours}h`,
      description: t("regional_dashboard.kpis.response_desc"),
      icon: <Clock3 className="size-4 text-slate-600" aria-hidden="true" />,
      tone: "neutral",
    },
  ];

  return (
    <section className="grid gap-3 md:grid-cols-2 xl:grid-cols-5">
      {cards.map((card) => (
        <Card key={card.label} className="transition-all duration-300 hover:shadow-md">
          <CardHeader className="flex flex-row items-start justify-between gap-2 space-y-0 pb-1 pt-3 px-4">
            <div>
              <p className="text-xs font-medium text-muted-foreground">{card.label}</p>
              <CardTitle className="mt-0.5 text-xl font-semibold">{card.value}</CardTitle>
            </div>
            <div className="flex size-8 items-center justify-center rounded-md bg-secondary">
              {card.icon}
            </div>
          </CardHeader>
          <CardContent className="px-4 pb-3 pt-1">
            <p className={cn("text-xs", getToneText(card.tone))}>{card.description}</p>
          </CardContent>
        </Card>
      ))}
    </section>
  );
}

function getToneText(tone: string) {
  if (tone === "good") return "text-green-700";
  if (tone === "warning") return "text-amber-700";
  if (tone === "critical") return "text-red-700";
  return "text-muted-foreground";
}

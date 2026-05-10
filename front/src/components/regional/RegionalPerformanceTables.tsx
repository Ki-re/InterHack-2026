import { ChevronDown, ChevronRight } from "lucide-react";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { cn } from "@/lib/utils";
import type {
  AgentPerformance,
  ClientExecution,
  ManagerPerformance,
  RegionSummary,
} from "@/types/regional-dashboard";

type RegionalPerformanceTablesProps = {
  region: RegionSummary;
  selectedManager: ManagerPerformance | null;
  selectedAgent: AgentPerformance | null;
  onSelectManager: (manager: ManagerPerformance) => void;
  onSelectAgent: (agent: AgentPerformance) => void;
  onResetManager: () => void;
  onResetAgent: () => void;
  t: (path: string, params?: Record<string, string | number>) => string;
};

export function RegionalPerformanceTables({
  region,
  selectedAgent,
  selectedManager,
  onResetAgent,
  onResetManager,
  onSelectAgent,
  onSelectManager,
  t,
}: RegionalPerformanceTablesProps) {
  return (
    <div className="space-y-0">
      <ManagersTable
        region={region}
        selectedManager={selectedManager}
        selectedAgent={selectedAgent}
        onSelectManager={onSelectManager}
        onSelectAgent={onSelectAgent}
        onResetManager={onResetManager}
        onResetAgent={onResetAgent}
        t={t}
      />
    </div>
  );
}

function ManagersTable({
  region,
  selectedManager,
  selectedAgent,
  onSelectManager,
  onSelectAgent,
  onResetManager,
  onResetAgent,
  t,
}: {
  region: RegionSummary;
  selectedManager: ManagerPerformance | null;
  selectedAgent: AgentPerformance | null;
  onSelectManager: (m: ManagerPerformance) => void;
  onSelectAgent: (a: AgentPerformance) => void;
  onResetManager: () => void;
  onResetAgent: () => void;
  t: (path: string, params?: Record<string, string | number>) => string;
}) {
  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle>{t("regional_dashboard.managers.title")}</CardTitle>
        <p className="mt-1 text-sm text-muted-foreground">{region.name}</p>
      </CardHeader>
      <CardContent className="p-0">
        <div className="overflow-x-auto">
          <table className="w-full min-w-[680px] text-left">
            <thead>
              <tr className="border-b text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                <th className="px-4 py-3">{t("regional_dashboard.table.name")}</th>
                <th className="px-4 py-3">{t("regional_dashboard.kpis.execution_score")}</th>
                <th className="px-4 py-3">{t("regional_dashboard.kpis.pending")}</th>
                <th className="px-4 py-3">{t("regional_dashboard.kpis.attended_rate")}</th>
                <th className="px-4 py-3">{t("regional_dashboard.kpis.high_risk")}</th>
                <th className="px-4 py-3">{t("regional_dashboard.table.action")}</th>
              </tr>
            </thead>
            <tbody>
              {region.managers.map((manager) => {
                const isExpanded = selectedManager?.id === manager.id;
                return (
                  <>
                    <tr
                      key={manager.id}
                      className={cn(
                        "border-b transition-colors",
                        isExpanded ? "bg-primary/5" : "hover:bg-secondary/50",
                      )}
                    >
                      <td className="px-4 py-3">
                        <p className="text-sm font-medium text-foreground">{manager.name}</p>
                        <p className="text-xs text-muted-foreground">{manager.email}</p>
                      </td>
                      <td className="px-4 py-3"><ScoreBadge score={manager.kpis.executionScore} /></td>
                      <td className="px-4 py-3 text-sm">{manager.kpis.pendingAlerts}</td>
                      <td className="px-4 py-3 text-sm">{manager.kpis.attendedRate}%</td>
                      <td className="px-4 py-3 text-sm">{manager.kpis.highRiskBacklog}</td>
                      <td className="px-4 py-3">
                        <button
                          type="button"
                          aria-label={isExpanded ? t("regional_dashboard.actions.collapse") : t("regional_dashboard.actions.zoom")}
                          className={cn(
                            "inline-flex size-8 items-center justify-center rounded-md border transition-colors",
                            isExpanded
                              ? "border-primary bg-primary/10 text-primary hover:bg-primary/20"
                              : "border-border bg-background text-muted-foreground hover:bg-secondary hover:text-foreground",
                          )}
                          onClick={() => (isExpanded ? onResetManager() : onSelectManager(manager))}
                        >
                          {isExpanded ? (
                            <ChevronDown className="size-4" aria-hidden="true" />
                          ) : (
                            <ChevronRight className="size-4" aria-hidden="true" />
                          )}
                        </button>
                      </td>
                    </tr>
                    {isExpanded && (
                      <tr key={`${manager.id}-agents`}>
                        <td colSpan={6} className="border-b bg-secondary/30 px-4 py-4">
                          <AgentsSubTable
                            manager={manager}
                            selectedAgent={selectedAgent}
                            onSelectAgent={onSelectAgent}
                            onResetAgent={onResetAgent}
                            t={t}
                          />
                        </td>
                      </tr>
                    )}
                  </>
                );
              })}
            </tbody>
          </table>
        </div>
      </CardContent>
    </Card>
  );
}

function AgentsSubTable({
  manager,
  selectedAgent,
  onSelectAgent,
  onResetAgent,
  t,
}: {
  manager: ManagerPerformance;
  selectedAgent: AgentPerformance | null;
  onSelectAgent: (a: AgentPerformance) => void;
  onResetAgent: () => void;
  t: (path: string, params?: Record<string, string | number>) => string;
}) {
  return (
    <div className="rounded-md border bg-background">
      <div className="border-b px-4 py-2">
        <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
          {t("regional_dashboard.agents.title")} · {manager.name}
        </p>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full min-w-[580px] text-left">
          <thead>
            <tr className="border-b text-xs font-semibold uppercase tracking-wide text-muted-foreground">
              <th className="px-4 py-2">{t("regional_dashboard.table.name")}</th>
              <th className="px-4 py-2">{t("regional_dashboard.kpis.execution_score")}</th>
              <th className="px-4 py-2">{t("regional_dashboard.kpis.pending")}</th>
              <th className="px-4 py-2">{t("regional_dashboard.kpis.attended_rate")}</th>
              <th className="px-4 py-2">{t("regional_dashboard.kpis.high_risk")}</th>
              <th className="px-4 py-2">{t("regional_dashboard.table.action")}</th>
            </tr>
          </thead>
          <tbody>
            {manager.agents.map((agent) => {
              const isExpanded = selectedAgent?.id === agent.id;
              return (
                <>
                  <tr
                    key={agent.id}
                    className={cn("border-b transition-colors", isExpanded ? "bg-primary/5" : "hover:bg-secondary/30")}
                  >
                    <td className="px-4 py-2">
                      <p className="text-sm font-medium text-foreground">{agent.name}</p>
                      <p className="text-xs text-muted-foreground">{agent.email}</p>
                    </td>
                    <td className="px-4 py-2"><ScoreBadge score={agent.kpis.executionScore} /></td>
                    <td className="px-4 py-2 text-sm">{agent.kpis.pendingAlerts}</td>
                    <td className="px-4 py-2 text-sm">{agent.kpis.attendedRate}%</td>
                    <td className="px-4 py-2 text-sm">{agent.kpis.highRiskBacklog}</td>
                    <td className="px-4 py-2">
                      <button
                        type="button"
                        aria-label={isExpanded ? t("regional_dashboard.actions.collapse") : t("regional_dashboard.actions.zoom")}
                        className={cn(
                          "inline-flex size-8 items-center justify-center rounded-md border transition-colors",
                          isExpanded
                            ? "border-primary bg-primary/10 text-primary hover:bg-primary/20"
                            : "border-border bg-background text-muted-foreground hover:bg-secondary hover:text-foreground",
                        )}
                        onClick={() => (isExpanded ? onResetAgent() : onSelectAgent(agent))}
                      >
                        {isExpanded ? (
                          <ChevronDown className="size-4" aria-hidden="true" />
                        ) : (
                          <ChevronRight className="size-4" aria-hidden="true" />
                        )}
                      </button>
                    </td>
                  </tr>
                  {isExpanded && (
                    <tr key={`${agent.id}-clients`}>
                      <td colSpan={6} className="border-b bg-secondary/20 px-4 py-4">
                        <ClientsSubTable agent={agent} t={t} />
                      </td>
                    </tr>
                  )}
                </>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function ClientsSubTable({
  agent,
  t,
}: {
  agent: AgentPerformance;
  t: (path: string, params?: Record<string, string | number>) => string;
}) {
  return (
    <div className="rounded-md border bg-background">
      <div className="border-b px-4 py-2">
        <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
          {t("regional_dashboard.clients.title")} · {agent.name}
        </p>
      </div>
      <div className="grid gap-3 p-3 sm:grid-cols-2 lg:grid-cols-3">
        {agent.clients.map((client) => (
          <ClientCard key={client.id} client={client} t={t} />
        ))}
      </div>
    </div>
  );
}

function ClientCard({
  client,
  t,
}: {
  client: ClientExecution;
  t: (path: string, params?: Record<string, string | number>) => string;
}) {
  return (
    <div className="rounded-md border bg-card px-4 py-3">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-sm font-medium text-foreground">{client.name}</p>
          <p className="mt-1 text-xs text-muted-foreground">
            {client.segment} · {client.customerValue}
          </p>
        </div>
        <ScoreBadge score={client.kpis.executionScore} />
      </div>
      <div className="mt-3 grid grid-cols-3 gap-2 text-xs text-muted-foreground">
        <MiniStat label={t("regional_dashboard.kpis.pending")} value={client.kpis.pendingAlerts} />
        <MiniStat label={t("regional_dashboard.kpis.high_risk")} value={client.kpis.highRiskBacklog} />
        <MiniStat label={t("regional_dashboard.clients.alerts")} value={client.kpis.totalAlerts} />
      </div>
    </div>
  );
}

function ScoreBadge({ score }: { score: number }) {
  return (
    <span className={cn("inline-flex rounded-full px-2.5 py-1 text-xs font-semibold", getScoreClass(score))}>
      {score}
    </span>
  );
}

function MiniStat({ label, value }: { label: string; value: number }) {
  return (
    <div className="rounded-md bg-secondary px-2 py-2">
      <p className="truncate">{label}</p>
      <p className="mt-1 font-semibold text-foreground">{value}</p>
    </div>
  );
}

function getScoreClass(score: number) {
  if (score >= 75) return "bg-green-50 text-green-700 border border-green-200";
  if (score >= 55) return "bg-amber-50 text-amber-700 border border-amber-200";
  return "bg-red-50 text-red-700 border border-red-200";
}

import { type ReactNode, useMemo, useState } from "react";
import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { motion } from "framer-motion";
import { AlertCircle, RefreshCcw, ShieldAlert } from "lucide-react";

import { getRegionalDashboard } from "@/api/regional-dashboard";
import { RegionalKpiCards } from "@/components/regional/RegionalKpiCards";
import { RegionDetailModal } from "@/components/regional/RegionDetailModal";
import { getRegionLabel, SpainRegionMap } from "@/components/regional/SpainRegionMap";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { cn } from "@/lib/utils";
import { useTranslation } from "@/contexts/LanguageContext";
import type {
  ExecutionKpis,
  RegionSlug,
  Underperformer,
} from "@/types/regional-dashboard";

const containerVariants = {
  hidden: { opacity: 0 },
  show: { opacity: 1, transition: { staggerChildren: 0.05 } },
};

const itemVariants = {
  hidden: { opacity: 0, y: 10 },
  show: { opacity: 1, y: 0 },
};

export function RegionalDashboard() {
  const { t } = useTranslation();
  const [selectedRegionSlug, setSelectedRegionSlug] = useState<RegionSlug | null>(null);
  const [selectedCcaa, setSelectedCcaa] = useState<string | null>(null);
  const [detailOpen, setDetailOpen] = useState(false);
  const dashboard = useQuery({
    queryKey: ["regional-dashboard", selectedCcaa],
    queryFn: () => getRegionalDashboard(selectedCcaa),
    placeholderData: keepPreviousData,
  });

  const selectedRegion = useMemo(() => {
    if (!selectedRegionSlug) return null;
    return dashboard.data?.regions.find((region) => region.slug === selectedRegionSlug) ?? null;
  }, [dashboard.data?.regions, selectedRegionSlug]);

  function handleSelectRegion(slug: RegionSlug) {
    if (selectedRegionSlug === slug) {
      setSelectedRegionSlug(null);
      setSelectedCcaa(null);
      setDetailOpen(false);
    } else {
      setSelectedRegionSlug(slug);
      setSelectedCcaa(null);
    }
  }

  if (dashboard.isLoading) {
    return <RegionalDashboardState message={t("regional_dashboard.loading")} />;
  }

  if (dashboard.isError || !dashboard.data) {
    return (
      <RegionalDashboardState
        message={t("regional_dashboard.error")}
        action={
          <Button type="button" variant="outline" onClick={() => dashboard.refetch()}>
            <RefreshCcw className="size-4" aria-hidden="true" />
            {t("regional_dashboard.actions.retry")}
          </Button>
        }
      />
    );
  }

  return (
    <motion.div variants={containerVariants} initial="hidden" animate="show" className="space-y-6">
      <motion.div variants={itemVariants}>
        <RegionalKpiCards
          kpis={selectedRegion ? selectedRegion.kpis : dashboard.data.kpis}
          t={t}
        />
      </motion.div>

      <motion.section variants={itemVariants} className="space-y-5">
        {/* Top row: fr columns fill the full width (same as KPI row above).
            items-stretch makes all cells the same height.
            Estat and Focus wrappers use position:relative + overflow:hidden so their
            absolutely-positioned content has 0 normal-flow height contribution →
            only the Map card determines the row height.
            Focus inner card uses h-full + flex-col + overflow-y-auto for inner scroll. */}
        <div className="grid gap-5 xl:grid-cols-[1.6fr_0.7fr_1fr] xl:items-stretch">
          {/* Map — direct grid item, natural height sets the row */}
          <SpainRegionMap
            regions={dashboard.data.regions}
            selectedSlug={selectedRegionSlug}
            selectedCcaa={selectedCcaa}
            onSelect={handleSelectRegion}
            onSelectCcaa={setSelectedCcaa}
            onOpenDetail={selectedRegion ? () => setDetailOpen(true) : undefined}
            t={t}
          />

          {/* Estat — absolute fill inside 0-height wrapper → matches map height exactly */}
          <div className="relative min-h-[300px] overflow-hidden xl:min-h-0">
            <div className="absolute inset-0">
              <RegionSnapshot
                regionName={selectedRegion ? getRegionLabel(selectedRegion.slug, t) : t("regional_dashboard.all_regions")}
                ccaaName={selectedCcaa ? t(`ccaa.${selectedCcaa}`) : undefined}
                kpis={selectedRegion ? selectedRegion.kpis : dashboard.data.kpis}
                t={t}
              />
            </div>
          </div>

          {/* Focus de risc — absolute fill + inner scroll */}
          <div className="relative min-h-[300px] overflow-hidden xl:min-h-0">
            <div className="absolute inset-0">
              <UnderperformersCard
                underperformers={dashboard.data.underperformers}
                t={t}
              />
            </div>
          </div>
        </div>
      </motion.section>

      {/* Region detail modal */}
      {detailOpen && selectedRegion && (
        <RegionDetailModal
          region={selectedRegion}
          onClose={() => setDetailOpen(false)}
          t={t}
        />
      )}
    </motion.div>
  );
}

function RegionSnapshot({
  kpis,
  regionName,
  ccaaName,
  t,
}: {
  kpis: ExecutionKpis;
  regionName: string;
  ccaaName?: string;
  t: (path: string, params?: Record<string, string | number>) => string;
}) {
  const scoreColor =
    kpis.status === "good"
      ? "text-green-700"
      : kpis.status === "warning"
        ? "text-amber-700"
        : "text-red-700";

  const barColor =
    kpis.status === "good"
      ? "bg-green-500"
      : kpis.status === "warning"
        ? "bg-amber-500"
        : "bg-red-500";

  return (
    <Card className="h-full">
      <CardContent className="h-full p-4">
        <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
          {t("regional_dashboard.snapshot.title")}
        </p>
        {ccaaName ? (
          <h2 className="mt-0.5 text-lg font-semibold text-foreground">
            <span className="text-muted-foreground">{regionName}</span>
            {" › "}
            {ccaaName}
          </h2>
        ) : (
          <h2 className="mt-0.5 text-lg font-semibold text-foreground">{regionName}</h2>
        )}
        {ccaaName && (
          <p className="mt-1 inline-block rounded border border-amber-200 bg-amber-50 px-2 py-0.5 text-[10px] text-amber-700">
            {t("regional_dashboard.snapshot.region_data_note")}
          </p>
        )}

        {/* Score gauge */}
        <div className="mt-3 flex items-center gap-3">
          <span className={cn("text-4xl font-bold tabular-nums", scoreColor)}>
            {kpis.executionScore}
          </span>
          <div className="flex-1">
            <p className="text-xs text-muted-foreground">{t("regional_dashboard.kpis.execution_score")}</p>
            <div className="mt-1 h-2 rounded-full bg-secondary">
              <div
                className={cn("h-2 rounded-full transition-all duration-500", barColor)}
                style={{ width: `${kpis.executionScore}%` }}
              />
            </div>
          </div>
        </div>

        {/* Stats grid — single column */}
        <div className="mt-3 grid grid-cols-1 gap-1.5">
          <SnapshotStat label={t("regional_dashboard.kpis.pending")} value={kpis.pendingAlerts} />
          <SnapshotStat label={t("regional_dashboard.kpis.high_risk")} value={kpis.highRiskBacklog} accent="red" />
          <SnapshotStat label={t("regional_dashboard.kpis.overdue")} value={kpis.overdueFollowups} accent="amber" />
          <SnapshotStat
            label={t("regional_dashboard.kpis.attended_rate")}
            value={kpis.attendedRate}
            suffix="%"
            accent="green"
          />
          <SnapshotStat label={t("regional_dashboard.kpis.response_time")} value={kpis.averageResponseHours ?? 0} suffix="h" />
          <SnapshotStat label={t("regional_dashboard.kpis.total_alerts")} value={kpis.totalAlerts} />
        </div>
      </CardContent>
    </Card>
  );
}

function SnapshotStat({
  label,
  value,
  suffix = "",
  accent,
}: {
  label: string;
  value: number;
  suffix?: string;
  accent?: "red" | "amber" | "green";
}) {
  const valueClass = accent === "red"
    ? "text-red-700"
    : accent === "amber"
      ? "text-amber-700"
      : accent === "green"
        ? "text-green-700"
        : "text-foreground";

  return (
    <div className="rounded-md border bg-background px-2.5 py-2">
      <p className="truncate text-[10px] uppercase tracking-wide text-muted-foreground">{label}</p>
      <p className={cn("mt-0.5 text-base font-semibold", valueClass)}>
        {value}{suffix}
      </p>
    </div>
  );
}

function UnderperformersCard({
  underperformers,
  t,
}: {
  underperformers: Underperformer[];
  t: (path: string, params?: Record<string, string | number>) => string;
}) {
  return (
    <Card className="flex h-full flex-col">
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between gap-3">
          <div>
            <CardTitle>{t("regional_dashboard.underperformers.title")}</CardTitle>
            <p className="mt-1 text-sm text-muted-foreground">
              {t("regional_dashboard.underperformers.subtitle")}
            </p>
          </div>
          <ShieldAlert className="size-5 shrink-0 text-red-600" aria-hidden="true" />
        </div>
      </CardHeader>
      {/* px-3 on both sides keeps inner boxes visually balanced (consistent margins) */}
      <CardContent className="min-h-0 flex-1 overflow-y-auto px-3 pb-3 pt-0">
        <div className="space-y-2.5">
        {underperformers.length === 0 && (
          <p className="text-sm text-muted-foreground">—</p>
        )}
        {underperformers.map((item) => {
          const regionLabel = t(`regional_dashboard.regions.${item.regionSlug}`);
          const isManager = item.level === "manager";

          return (
            <div key={`${item.level}-${item.id}`} className="rounded-md border bg-background px-3 py-2.5">
              <div className="flex items-start justify-between gap-2">
                <div className="min-w-0">
                  {/* Name + region on same line */}
                  <p className="truncate text-sm font-medium text-foreground">
                    {item.name}
                    <span className="ml-1 text-xs font-normal text-muted-foreground">· {regionLabel}</span>
                  </p>
                  {/* Role or manager line below */}
                  {isManager ? (
                    <span className="mt-0.5 inline-flex items-center rounded px-1.5 py-0.5 text-[10px] font-medium bg-slate-100 text-slate-700">
                      {t("regional_dashboard.underperformers.role_manager")}
                    </span>
                  ) : item.parentName ? (
                    <p className="mt-0.5 text-xs text-muted-foreground">
                      {t("regional_dashboard.underperformers.manager_label")} {item.parentName}
                    </p>
                  ) : null}
                </div>
                <UnderScore score={item.executionScore} />
              </div>
              <div className="mt-2 grid grid-cols-3 gap-1.5 text-xs text-muted-foreground">
                <MiniUnder label={t("regional_dashboard.kpis.pending")} value={item.pendingAlerts} />
                <MiniUnder label={t("regional_dashboard.kpis.high_risk")} value={item.highRiskBacklog} />
                <MiniUnder label={t("regional_dashboard.kpis.overdue")} value={item.overdueFollowups} />
              </div>
            </div>
          );
        })}
        </div>
      </CardContent>
    </Card>
  );
}

function UnderScore({ score }: { score: number }) {
  const cls =
    score >= 75
      ? "bg-green-50 text-green-700 border border-green-200"
      : score >= 55
        ? "bg-amber-50 text-amber-700 border border-amber-200"
        : "bg-red-50 text-red-700 border border-red-200";
  return (
    <span className={cn("inline-flex shrink-0 rounded-full px-2 py-0.5 text-xs font-semibold", cls)}>
      {score}
    </span>
  );
}

function MiniUnder({ label, value }: { label: string; value: number }) {
  return (
    <div className="rounded bg-secondary px-2 py-1.5">
      <p className="truncate text-[9px]">{label}</p>
      <p className="font-semibold text-foreground">{value}</p>
    </div>
  );
}

function RegionalDashboardState({ action, message }: { action?: ReactNode; message: string }) {
  return (
    <div className="flex min-h-[50vh] items-center justify-center">
      <div className="rounded-lg border bg-card px-6 py-5 text-center shadow-sm">
        <AlertCircle className="mx-auto size-6 text-primary" aria-hidden="true" />
        <p className="mt-3 text-sm text-muted-foreground">{message}</p>
        {action ? <div className="mt-4">{action}</div> : null}
      </div>
    </div>
  );
}

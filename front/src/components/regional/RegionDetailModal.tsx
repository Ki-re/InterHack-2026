import { useState } from "react";
import { Users, X } from "lucide-react";

import { RegionalPerformanceTables } from "@/components/regional/RegionalPerformanceTables";
import { getRegionLabel } from "@/components/regional/SpainRegionMap";
import { cn } from "@/lib/utils";
import type { AgentPerformance, ManagerPerformance, RegionSummary } from "@/types/regional-dashboard";

type RegionDetailModalProps = {
  region: RegionSummary;
  onClose: () => void;
  t: (path: string, params?: Record<string, string | number>) => string;
};

export function RegionDetailModal({ region, onClose, t }: RegionDetailModalProps) {
  const [selectedManager, setSelectedManager] = useState<ManagerPerformance | null>(null);
  const [selectedAgent, setSelectedAgent] = useState<AgentPerformance | null>(null);

  function handleSelectManager(manager: ManagerPerformance) {
    setSelectedManager(manager);
    setSelectedAgent(null);
  }

  function handleResetManager() {
    setSelectedManager(null);
    setSelectedAgent(null);
  }

  return (
    <div
      aria-modal="true"
      role="dialog"
      aria-label={getRegionLabel(region.slug, t)}
      className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/40 px-4 py-6"
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <div className="flex w-full max-w-5xl flex-col rounded-xl border bg-card shadow-2xl"
        style={{ maxHeight: "90vh" }}>
        {/* Header */}
        <div className="flex shrink-0 items-center justify-between gap-4 border-b px-6 py-4">
          <div className="flex items-center gap-3">
            <div className={cn(
              "flex size-9 items-center justify-center rounded-md",
              "bg-primary/10",
            )}>
              <Users className="size-5 text-primary" aria-hidden="true" />
            </div>
            <div>
              <h2 className="text-base font-semibold text-foreground">
                {t("regional_dashboard.managers.title")}
              </h2>
              <p className="text-sm text-muted-foreground">
                {"Regió " + getRegionLabel(region.slug, t)}
              </p>
            </div>
          </div>
          <button
            type="button"
            aria-label={t("modal.close")}
            className="inline-flex size-8 items-center justify-center rounded-md text-muted-foreground transition-colors hover:bg-secondary hover:text-foreground"
            onClick={onClose}
          >
            <X className="size-4" aria-hidden="true" />
          </button>
        </div>

        {/* Scrollable body */}
        <div className="min-h-0 flex-1 overflow-y-auto p-6">
          <RegionalPerformanceTables
            region={region}
            selectedManager={selectedManager}
            selectedAgent={selectedAgent}
            onSelectManager={handleSelectManager}
            onSelectAgent={setSelectedAgent}
            onResetManager={handleResetManager}
            onResetAgent={() => setSelectedAgent(null)}
            t={t}
          />
        </div>
      </div>
    </div>
  );
}

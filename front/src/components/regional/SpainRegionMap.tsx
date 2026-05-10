import { useMemo } from "react";
import { geoMercator, geoPath } from "d3-geo";
import { Info, MapPinned } from "lucide-react";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { cn } from "@/lib/utils";
import type { RegionSlug, RegionSummary } from "@/types/regional-dashboard";
import spainGeoJson from "@/data/spain-communities.json";

type SpainRegionMapProps = {
  regions: RegionSummary[];
  selectedSlug: RegionSlug | null;
  selectedCcaa: string | null;
  onSelect: (slug: RegionSlug) => void;
  onSelectCcaa: (cod: string | null) => void;
  onOpenDetail?: () => void;
  t: (path: string, params?: Record<string, string | number>) => string;
};

const WIDTH = 560;
const HEIGHT = 310;

const projection = geoMercator()
  .center([-3.5, 40.4])
  .scale(1600)
  .translate([WIDTH / 2, HEIGHT / 2]);

const pathGen = geoPath().projection(projection);

const CCAA_TO_REGION: Record<string, RegionSlug | null> = {
  "01": "south",   // Andalucía
  "02": "est",     // Aragón
  "03": "north",   // Asturias
  "04": null,      // Baleares — skip
  "05": null,      // Canarias — skip
  "06": "north",   // Cantabria
  "07": "north",   // Castilla-León
  "08": "south",   // Castilla-La Mancha
  "09": "est",     // Catalunya
  "10": "est",     // Comunitat Valenciana
  "11": "south",   // Extremadura
  "12": "north",   // Galicia
  "13": "south",   // Madrid
  "14": "est",     // Murcia
  "15": "north",   // Navarra
  "16": "north",   // País Basc
  "17": "north",   // La Rioja
  "18": null,      // Ceuta — skip
  "19": null,      // Melilla — skip
};

export function SpainRegionMap({
  regions,
  selectedSlug,
  selectedCcaa,
  onSelect,
  onSelectCcaa,
  onOpenDetail,
  t,
}: SpainRegionMapProps) {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const features = useMemo(() => (spainGeoJson as any).features as any[], []);

  function handlePathClick(cod: string, slug: RegionSlug) {
    if (!selectedSlug) {
      // Level 1: no region selected → select region
      onSelect(slug);
      return;
    }
    if (selectedSlug !== slug) {
      // Clicked a different region → switch region, clear CCAA
      onSelect(slug);
      return;
    }
    // Same region: toggle CCAA selection
    if (selectedCcaa === cod) {
      onSelectCcaa(null);
    } else {
      onSelectCcaa(cod);
    }
  }

  function getCcaaLabel(cod: string) {
    return t(`ccaa.${cod}`);
  }

  return (
    <Card className="overflow-hidden">
      <CardHeader className="flex flex-row items-center justify-between gap-3 pb-3">
        <div>
          <CardTitle>{t("regional_dashboard.map.title")}</CardTitle>
          <p className="mt-1 text-sm text-muted-foreground">{t("regional_dashboard.map.subtitle")}</p>
        </div>
        <div className="flex items-center gap-2">
          {selectedSlug && onOpenDetail ? (
            <button
              type="button"
              onClick={onOpenDetail}
              className="inline-flex items-center gap-1.5 rounded-md border border-primary/30 bg-primary/5 px-3 py-1.5 text-xs font-medium text-primary transition-colors hover:bg-primary/10"
            >
              <Info className="size-3.5" aria-hidden="true" />
              {t("regional_dashboard.actions.open_detail")}
            </button>
          ) : (
            <div className="flex size-10 items-center justify-center rounded-md bg-secondary">
              <MapPinned className="size-5 text-primary" aria-hidden="true" />
            </div>
          )}
        </div>
      </CardHeader>
      <CardContent className="p-0">
        <div className="rounded-none bg-sky-50 p-3">
          <svg
            viewBox={`0 0 ${WIDTH} ${HEIGHT}`}
            className="mx-auto h-auto w-full"
            role="img"
            aria-label={t("regional_dashboard.map.aria")}
            onClick={(e) => {
              // Click on SVG background (not a path) → deselect CCAA
              if ((e.target as SVGElement).tagName === "svg" && selectedCcaa) {
                onSelectCcaa(null);
              }
            }}
          >
            {features.map((feature) => {
              // eslint-disable-next-line @typescript-eslint/no-explicit-any
              const cod: string = (feature as any).properties?.cod_ccaa ?? "";
              const slug = CCAA_TO_REGION[cod];
              if (!slug) return null;

              const region = regions.find((r) => r.slug === slug);
              const isSelectedRegion = selectedSlug === slug;
              const isSelectedCcaa = selectedCcaa === cod;
              // eslint-disable-next-line @typescript-eslint/no-explicit-any
              const d = pathGen(feature as any);
              if (!d) return null;

              // Visual states
              let opacity = 1;
              let stroke = "white";
              let strokeWidth = 0.8;

              if (selectedSlug === null) {
                // No selection — all normal
                opacity = 1;
              } else if (!isSelectedRegion) {
                // Different region — dimmed
                opacity = 0.3;
              } else if (selectedCcaa === null) {
                // This region selected, no CCAA — all full
                opacity = 1;
              } else if (isSelectedCcaa) {
                opacity = 1;
              } else {
                // Same region, different CCAA — dimmed
                opacity = 0.45;
              }

              const label = selectedSlug === slug
                ? `${getCcaaLabel(cod)} — ${t("regional_dashboard.map.score", { score: region?.kpis.executionScore ?? 0 })}`
                : getRegionLabel(slug, t);

              return (
                <path
                  key={cod}
                  d={d}
                  fill={region ? getStatusFill(region.kpis.status) : "#e2e8f0"}
                  stroke={stroke}
                  strokeWidth={strokeWidth}
                  opacity={opacity}
                  style={{ cursor: "pointer" }}
                  onClick={() => handlePathClick(cod, slug)}
                  onKeyDown={(e: React.KeyboardEvent) => {
                    if (e.key === "Enter" || e.key === " ") handlePathClick(cod, slug);
                  }}
                  tabIndex={0}
                  role="button"
                  aria-label={label}
                  aria-pressed={isSelectedCcaa || (!selectedCcaa && isSelectedRegion)}
                  className="focus:outline-none"
                />
              );
            })}
          </svg>
        </div>

        {/* Region buttons */}
        <div className="flex flex-wrap gap-2 px-3 pb-3 pt-2">
          {regions.map((region) => (
            <button
              key={region.slug}
              type="button"
              className={cn(
                "flex flex-1 items-center justify-between gap-2 rounded-md border px-3 py-2 text-left transition-colors",
                selectedSlug === region.slug
                  ? "border-primary bg-primary/5"
                  : "bg-background hover:bg-secondary",
              )}
              onClick={() => onSelect(region.slug)}
            >
              <div className="min-w-0">
                <span className="block truncate text-sm font-medium text-foreground">
                  {t("regional_dashboard.region_prefix") + getRegionLabel(region.slug, t)}
                </span>
              </div>
              <span className={cn("size-2.5 shrink-0 rounded-full", getStatusDot(region.kpis.status))} />
            </button>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}

export function getRegionLabel(
  slug: RegionSlug,
  t: (path: string, params?: Record<string, string | number>) => string,
) {
  return t(`regional_dashboard.regions.${slug}`);
}

function getStatusFill(status: string) {
  if (status === "good") return "#16a34a";
  if (status === "warning") return "#f59e0b";
  return "#dc2626";
}

function getStatusDot(status: string) {
  if (status === "good") return "bg-green-600";
  if (status === "warning") return "bg-amber-500";
  return "bg-red-600";
}

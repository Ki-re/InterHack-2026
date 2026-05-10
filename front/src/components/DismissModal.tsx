import { useState } from "react";
import { Trash2, X } from "lucide-react";

import { Button } from "@/components/ui/button";
import { useTranslation } from "@/contexts/LanguageContext";
import type { SalesAlert } from "@/types/alerts";

type DismissModalProps = {
  alert: SalesAlert | null;
  onClose: () => void;
  onConfirm: (alertId: string, reason?: string) => void;
};

export function DismissModal({ alert, onClose, onConfirm }: DismissModalProps) {
  const { t } = useTranslation();
  const [reason, setReason] = useState("");

  if (!alert) return null;

  function handleConfirm() {
    onConfirm(alert!.id, reason.trim() || undefined);
    setReason("");
    onClose();
  }

  function handleClose() {
    setReason("");
    onClose();
  }

  return (
    <div
      aria-modal="true"
      className="fixed inset-0 z-40 flex items-center justify-center bg-slate-950/35 px-4 py-6"
      role="dialog"
    >
      <div className="w-full max-w-md rounded-lg border bg-card shadow-xl">
        {/* Header */}
        <div className="flex items-start justify-between gap-4 border-b px-5 py-4">
          <div className="flex items-center gap-2">
            <Trash2 className="size-5 text-destructive" aria-hidden="true" />
            <div>
              <h2 className="text-base font-semibold text-foreground">{t("dismiss.title")}</h2>
              <p className="mt-0.5 text-sm text-muted-foreground">{alert.clientName}</p>
            </div>
          </div>
          <Button aria-label={t("modal.close")} size="icon" type="button" variant="ghost" onClick={handleClose}>
            <X className="size-4" aria-hidden="true" />
          </Button>
        </div>

        {/* Body */}
        <div className="space-y-4 px-5 py-5">
          <p className="text-sm text-muted-foreground">{t("dismiss.description")}</p>

          <div className="space-y-1.5">
            <label className="text-sm font-medium text-foreground" htmlFor="dismiss-reason">
              {t("dismiss.reason_label")}
            </label>
            <textarea
              id="dismiss-reason"
              className="w-full resize-none rounded-md border bg-background px-3 py-2 text-sm outline-none transition-colors placeholder:text-muted-foreground focus:border-ring focus:ring-2 focus:ring-ring/20"
              placeholder={t("dismiss.reason_placeholder")}
              rows={3}
              value={reason}
              onChange={(e) => setReason(e.target.value)}
            />
          </div>

          <div className="flex gap-2 pt-1">
            <Button type="button" variant="outline" className="flex-1" onClick={handleClose}>
              {t("dismiss.cancel")}
            </Button>
            <Button type="button" variant="destructive" className="flex-1" onClick={handleConfirm}>
              <Trash2 className="size-4" aria-hidden="true" />
              {t("dismiss.confirm")}
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}

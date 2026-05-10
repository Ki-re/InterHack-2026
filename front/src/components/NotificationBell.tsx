import { Bell } from "lucide-react";
import { useRef, useState } from "react";

import { useNotifications } from "@/hooks/useNotifications";
import { useOnClickOutside } from "@/hooks/useOnClickOutside";
import { Button } from "@/components/ui/button";
import { useTranslation } from "@/contexts/LanguageContext";
import type { Notification } from "@/types/notifications";

type TFn = (path: string, params?: Record<string, string | number>) => string;

function formatRelativeTime(isoString: string, t: TFn): string {
  const diff = Date.now() - new Date(isoString).getTime();
  const minutes = Math.floor(diff / 60000);
  if (minutes < 60) return t("time.minutes_ago", { n: minutes });
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return t("time.hours_ago", { n: hours });
  return t("time.days_ago", { n: Math.floor(hours / 24) });
}

function NotificationItem({
  notification,
  onRead,
  t,
}: {
  notification: Notification;
  onRead: (id: number) => void;
  t: TFn;
}) {
  const isUnread = notification.read_at === null;

  return (
    <div
      className={`flex cursor-pointer gap-3 border-b px-4 py-3 last:border-0 hover:bg-muted/50 ${isUnread ? "bg-blue-50/60 dark:bg-blue-950/20" : ""}`}
      onClick={() => isUnread && onRead(notification.id)}
    >
      {isUnread && <div className="mt-1.5 size-2 shrink-0 rounded-full bg-blue-500" />}
      {!isUnread && <div className="mt-1.5 size-2 shrink-0" />}
      <div className="min-w-0 flex-1">
        <p className="text-sm font-medium leading-snug">{notification.title}</p>
        <p className="mt-0.5 text-xs text-muted-foreground leading-relaxed">{notification.body}</p>
        <p className="mt-1 text-xs text-muted-foreground/70">
          {formatRelativeTime(notification.created_at, t)}
        </p>
      </div>
    </div>
  );
}

export function NotificationBell() {
  const [open, setOpen] = useState(false);
  const { notifications, unreadCount, markRead, markAllRead } = useNotifications();
  const panelRef = useRef<HTMLDivElement>(null);
  const { t } = useTranslation();

  useOnClickOutside(panelRef, () => setOpen(false));

  return (
    <div className="relative" ref={panelRef}>
      <Button
        variant="outline"
        size="sm"
        type="button"
        className="relative"
        onClick={() => setOpen((v) => !v)}
        aria-label={t("notification.bell_aria")}
      >
        <Bell className="size-4" />
        {unreadCount > 0 && (
          <span className="absolute -right-1.5 -top-1.5 flex size-4 items-center justify-center rounded-full bg-red-500 text-[10px] font-bold text-white">
            {unreadCount > 9 ? "9+" : unreadCount}
          </span>
        )}
      </Button>

      {open && (
        <div className="absolute right-0 top-full z-50 mt-2 w-80 overflow-hidden rounded-lg border bg-card shadow-lg">
          <div className="flex items-center justify-between border-b px-4 py-3">
            <span className="text-sm font-semibold">{t("notification.title")}</span>
            {unreadCount > 0 && (
              <button
                className="text-xs text-blue-500 hover:underline"
                onClick={markAllRead}
              >
                {t("notification.mark_all_read")}
              </button>
            )}
          </div>

          <div className="max-h-96 overflow-y-auto">
            {notifications.length === 0 ? (
              <p className="px-4 py-8 text-center text-sm text-muted-foreground">
                {t("notification.empty")}
              </p>
            ) : (
              notifications.map((n) => (
                <NotificationItem key={n.id} notification={n} onRead={markRead} t={t} />
              ))
            )}
          </div>
        </div>
      )}
    </div>
  );
}

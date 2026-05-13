import { useCallback, useEffect, useState } from "react";

import { apiRequest } from "@/api/client";
import { useDemoMode } from "@/contexts/DemoModeContext";
import type { Notification } from "@/types/notifications";

const API_BASE_URL = import.meta.env.VITE_API_URL?.replace(/\/$/, "") ?? "http://localhost:8000";

async function fetchNotifications(agentId: number): Promise<Notification[]> {
  return apiRequest<Notification[]>(`/notifications?agent_id=${agentId}`);
}

async function patchRead(notificationId: number, agentId: number): Promise<void> {
  await fetch(`${API_BASE_URL}/notifications/${notificationId}/read?agent_id=${agentId}`, {
    method: "PATCH",
  });
}

async function patchReadAll(agentId: number): Promise<void> {
  await fetch(`${API_BASE_URL}/notifications/read-all?agent_id=${agentId}`, {
    method: "PATCH",
  });
}

export function useNotifications(agentId: number | null) {
  const { isDemoMode } = useDemoMode();
  const [notifications, setNotifications] = useState<Notification[]>([]);

  useEffect(() => {
    if (agentId === null) {
      setNotifications([]);
      return;
    }

    let cancelled = false;

    async function load() {
      try {
        const data = await fetchNotifications(agentId!);
        if (!cancelled) setNotifications(data);
      } catch {
        // non-critical
      }
    }

    void load();
    const interval = setInterval(load, 60_000);
    return () => { cancelled = true; clearInterval(interval); };
  }, [agentId]);

  const unreadCount = notifications.filter((n) => n.read_at === null).length;

  const markRead = useCallback(async (id: number) => {
    if (agentId === null) return;
    setNotifications((prev) =>
      prev.map((n) => (n.id === id ? { ...n, read_at: new Date().toISOString() } : n)),
    );
    if (!isDemoMode) {
      await patchRead(id, agentId).catch(() => {});
    }
  }, [agentId, isDemoMode]);

  const markAllRead = useCallback(async () => {
    if (agentId === null) return;
    const now = new Date().toISOString();
    setNotifications((prev) => prev.map((n) => ({ ...n, read_at: n.read_at ?? now })));
    if (!isDemoMode) {
      await patchReadAll(agentId).catch(() => {});
    }
  }, [agentId, isDemoMode]);

  return { notifications, unreadCount, markRead, markAllRead };
}

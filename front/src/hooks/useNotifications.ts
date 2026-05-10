import { useCallback, useState } from "react";

import type { Notification } from "@/types/notifications";

const MOCK_NOTIFICATIONS: Notification[] = [
  {
    id: 1,
    alert_id: "alert-001",
    title: "⚠️ Alerta prioritat alta: Clínica Dental Armonía",
    body: "El client Clínica Dental Armonía porta 5 dies amb una alerta d'alt risc sense resoldre. Revisa i gestiona l'alerta.",
    created_at: new Date(Date.now() - 1000 * 60 * 60 * 2).toISOString(),
    read_at: null,
  },
  {
    id: 2,
    alert_id: "alert-004",
    title: "⚠️ Alerta prioritat alta: Estudi Dental Sants",
    body: "El client Estudi Dental Sants porta 7 dies amb una alerta d'alt risc sense resoldre. Revisa i gestiona l'alerta.",
    created_at: new Date(Date.now() - 1000 * 60 * 60 * 3).toISOString(),
    read_at: null,
  },
  {
    id: 3,
    alert_id: "alert-005",
    title: "⚠️ Alerta prioritat alta: Clínica Dental Provença",
    body: "El client Clínica Dental Provença porta 4 dies amb una alerta d'alt risc sense resoldre. Revisa i gestiona l'alerta.",
    created_at: new Date(Date.now() - 1000 * 60 * 60 * 5).toISOString(),
    read_at: null,
  },
  {
    id: 4,
    alert_id: "alert-008",
    title: "⚠️ Alerta prioritat alta: Clínica Dental Sabadell Nord",
    body: "El client Clínica Dental Sabadell Nord porta 3 dies amb una alerta d'alt risc sense resoldre. Revisa i gestiona l'alerta.",
    created_at: new Date(Date.now() - 1000 * 60 * 60 * 8).toISOString(),
    read_at: null,
  },
];

export function useNotifications() {
  const [notifications, setNotifications] = useState<Notification[]>(MOCK_NOTIFICATIONS);

  const unreadCount = notifications.filter((n) => n.read_at === null).length;

  const markRead = useCallback((id: number) => {
    setNotifications((prev) =>
      prev.map((n) => (n.id === id ? { ...n, read_at: new Date().toISOString() } : n)),
    );
  }, []);

  const markAllRead = useCallback(() => {
    const now = new Date().toISOString();
    setNotifications((prev) => prev.map((n) => ({ ...n, read_at: n.read_at ?? now })));
  }, []);

  return { notifications, unreadCount, markRead, markAllRead };
}

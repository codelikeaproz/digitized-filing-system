import { useCallback, useEffect, useState } from "react";
import { clearNotifications, fetchNotificationCount, fetchNotifications } from "@/lib/system-settings";
import type { AppNotification } from "@/types";

const POLL_INTERVAL_MS = 60_000;

export function useNotifications() {
  const [notifications, setNotifications] = useState<AppNotification[]>([]);
  const [unreadCount, setUnreadCount] = useState(0);
  const [loading, setLoading] = useState(true);

  const refresh = useCallback(async () => {
    try {
      const [items, count] = await Promise.all([fetchNotifications(), fetchNotificationCount()]);
      setNotifications(items);
      setUnreadCount(count);
    } catch {
      // Keep prior state on transient failures.
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    refresh();
    const timer = window.setInterval(refresh, POLL_INTERVAL_MS);
    return () => window.clearInterval(timer);
  }, [refresh]);

  const clearAll = useCallback(async () => {
    try {
      await clearNotifications();
      setNotifications([]);
      setUnreadCount(0);
    } catch {
      // Keep prior state on failure.
    }
  }, []);

  return { notifications, unreadCount, loading, refresh, clearAll };
}

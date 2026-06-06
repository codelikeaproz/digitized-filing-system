import { Bell } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { useNotifications } from "@/hooks/useNotifications";
import { cn } from "@/lib/utils";

const LEVEL_STYLES: Record<string, string> = {
  warning: "border-amber-200 bg-amber-50 text-amber-900",
  alert: "border-orange-200 bg-orange-50 text-orange-900",
  critical: "border-red-200 bg-red-50 text-red-900",
  exceeded: "border-red-300 bg-red-100 text-red-950",
};

function formatTimestamp(value: string) {
  if (!value) return "";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString();
}

export function NotificationBell() {
  const { notifications, unreadCount, loading } = useNotifications();

  return (
    <Popover>
      <PopoverTrigger asChild>
        <Button
          variant="ghost"
          size="icon"
          className="relative text-muted-foreground hover:text-foreground"
          aria-label="Notifications"
        >
          <Bell className="h-5 w-5" />
          {unreadCount > 0 ? (
            <span className="absolute -right-0.5 -top-0.5 flex h-4 min-w-4 items-center justify-center rounded-full bg-destructive px-1 text-[10px] font-bold text-destructive-foreground">
              {unreadCount > 99 ? "99+" : unreadCount}
            </span>
          ) : null}
        </Button>
      </PopoverTrigger>
      <PopoverContent align="end" className="w-96 p-0">
        <div className="border-b px-4 py-3">
          <p className="text-sm font-semibold">Notifications</p>
          <p className="text-xs text-muted-foreground">System storage alerts and updates</p>
        </div>
        <div className="max-h-96 overflow-y-auto">
          {loading && notifications.length === 0 ? (
            <p className="px-4 py-6 text-sm text-muted-foreground">Loading notifications...</p>
          ) : notifications.length === 0 ? (
            <p className="px-4 py-6 text-sm text-muted-foreground">No notifications yet.</p>
          ) : (
            notifications.map((notification) => (
              <div key={notification.id} className="border-b px-4 py-3 last:border-b-0">
                <div className="flex items-start justify-between gap-2">
                  <p className="text-sm font-semibold">{notification.title}</p>
                  <span
                    className={cn(
                      "shrink-0 rounded border px-1.5 py-0.5 text-[10px] font-medium uppercase",
                      LEVEL_STYLES[notification.level] ?? LEVEL_STYLES.warning
                    )}
                  >
                    {notification.level}
                  </span>
                </div>
                <p className="mt-1 whitespace-pre-line text-xs text-muted-foreground">{notification.message}</p>
                <p className="mt-2 text-[10px] text-muted-foreground">{formatTimestamp(notification.createdAt)}</p>
              </div>
            ))
          )}
        </div>
      </PopoverContent>
    </Popover>
  );
}

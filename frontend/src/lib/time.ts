const MANILA_TIME_ZONE = "Asia/Manila";

function normalizeTimestamp(value: string | number | Date) {
  if (value instanceof Date || typeof value === "number") return value;
  if (/^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$/.test(value)) {
    return `${value.replace(" ", "T")}+08:00`;
  }
  return value;
}

export function formatManilaDateTime(value?: string | number | Date | null) {
  if (!value) return "-";
  const date = new Date(normalizeTimestamp(value));
  if (Number.isNaN(date.getTime())) return String(value);
  return date.toLocaleString("en-PH", {
    timeZone: MANILA_TIME_ZONE,
    year: "numeric",
    month: "short",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: true,
  });
}

export function formatManilaDate(value?: string | number | Date | null) {
  if (!value) return "-";
  const date = new Date(normalizeTimestamp(value));
  if (Number.isNaN(date.getTime())) return String(value);
  return date.toLocaleDateString("en-PH", {
    timeZone: MANILA_TIME_ZONE,
    year: "numeric",
    month: "short",
    day: "2-digit",
  });
}

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

/** e.g. May 31, 2:30 pm — for document table */
export function formatDocumentTableDate(value?: string | number | Date | null) {
  if (!value) return "—";
  const date = new Date(normalizeTimestamp(value));
  if (Number.isNaN(date.getTime())) return String(value);

  const parts = new Intl.DateTimeFormat("en-US", {
    timeZone: MANILA_TIME_ZONE,
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
    hour12: true,
  }).formatToParts(date);

  const month = parts.find((part) => part.type === "month")?.value ?? "";
  const day = parts.find((part) => part.type === "day")?.value ?? "";
  const hour = parts.find((part) => part.type === "hour")?.value ?? "";
  const minute = parts.find((part) => part.type === "minute")?.value ?? "";
  const dayPeriod = parts.find((part) => part.type === "dayPeriod")?.value?.toLowerCase() ?? "";

  return `${month} ${day}, ${hour}:${minute} ${dayPeriod}`.trim();
}

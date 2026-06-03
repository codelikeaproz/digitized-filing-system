import { type ClassValue, clsx } from "clsx"
import { twMerge } from "tailwind-merge"

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

/** Cabinet 2 before Cabinet 11 — numeric segments in names sort naturally. */
export function compareByNaturalName(a: string, b: string): number {
  return (a || "").localeCompare(b || "", undefined, { numeric: true, sensitivity: "base" })
}

export function sortByNaturalName<T extends { name?: string }>(items: T[]): T[] {
  return [...items].sort((a, b) => compareByNaturalName(a.name ?? "", b.name ?? ""))
}

/** "ralph jay" → "Ralph Jay"; supports hyphenated parts (e.g. Mary-Jane). */
export function formatPersonName(value: string): string {
  const cleaned = (value || "").trim()
  if (!cleaned) return ""
  const capitalizePart = (part: string) =>
    part ? part.charAt(0).toUpperCase() + part.slice(1).toLowerCase() : ""
  return cleaned
    .split(/\s+/)
    .map((word) => word.split("-").map(capitalizePart).join("-"))
    .join(" ")
}

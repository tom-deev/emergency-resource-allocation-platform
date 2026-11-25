export const IST_TIMEZONE = "Asia/Kolkata";

export const SEVERITY_TO_PRIORITY = {
  CRITICAL: "P1",
  HIGH: "P2",
  MEDIUM: "P3",
  LOW: "P4",
};

export function derivePriority(severity) {
  return SEVERITY_TO_PRIORITY[severity] || "P4";
}

export function formatIstDate(isoString) {
  if (!isoString) return "—";
  const date = new Date(isoString);
  if (Number.isNaN(date.getTime())) return "—";
  return new Intl.DateTimeFormat("en-IN", {
    timeZone: IST_TIMEZONE,
    day: "2-digit",
    month: "short",
    year: "numeric",
  }).format(date);
}

export function formatIstTime(isoString) {
  if (!isoString) return "—";
  const date = new Date(isoString);
  if (Number.isNaN(date.getTime())) return "—";
  const formatted = new Intl.DateTimeFormat("en-IN", {
    timeZone: IST_TIMEZONE,
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: true,
  }).format(date);
  return `${formatted} IST`;
}

export function formatIstDateTime(isoString) {
  if (!isoString) return "—";
  const date = new Date(isoString);
  if (Number.isNaN(date.getTime())) return "—";
  return `${formatIstDate(isoString)}, ${formatIstTime(isoString)}`;
}

/**
 * Return YYYY-MM-DD in Asia/Kolkata (IST) for date-picker filtering.
 */
export function getIstDateKey(isoString) {
  if (!isoString) return "";
  const date = new Date(isoString);
  if (Number.isNaN(date.getTime())) return "";
  const parts = new Intl.DateTimeFormat("en-CA", {
    timeZone: IST_TIMEZONE,
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  }).formatToParts(date);
  const year = parts.find((p) => p.type === "year")?.value || "";
  const month = parts.find((p) => p.type === "month")?.value || "";
  const day = parts.find((p) => p.type === "day")?.value || "";
  return year && month && day ? `${year}-${month}-${day}` : "";
}

export function formatElapsedFromIso(isoString, nowMs = Date.now()) {
  if (!isoString) return "—";
  const ts = new Date(isoString).getTime();
  if (Number.isNaN(ts)) return "—";
  const totalSec = Math.max(0, Math.floor((nowMs - ts) / 1000));
  return formatDurationSeconds(totalSec);
}

export function formatDurationSeconds(totalSeconds) {
  if (totalSeconds === null || totalSeconds === undefined || totalSeconds < 0) {
    return "—";
  }
  const sec = Math.floor(totalSeconds);
  if (sec < 60) return `${sec}s`;
  const mins = Math.floor(sec / 60);
  if (mins < 60) return `${mins}m`;
  const hours = Math.floor(mins / 60);
  const remMins = mins % 60;
  if (hours < 24) return remMins > 0 ? `${hours}h ${remMins}m` : `${hours}h`;
  const days = Math.floor(hours / 24);
  const remHours = hours % 24;
  return remHours > 0 ? `${days}d ${remHours}h` : `${days}d`;
}

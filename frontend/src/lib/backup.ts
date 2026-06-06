const BACKEND_URL = (import.meta.env.VITE_API_URL || "http://127.0.0.1:8000").replace(/\/$/, "");

function getFileNameFromDisposition(disposition: string | null) {
  if (!disposition) return null;
  const utf8Match = disposition.match(/filename\*=UTF-8''([^;]+)/i);
  if (utf8Match?.[1]) return decodeURIComponent(utf8Match[1]);
  const fileNameMatch = disposition.match(/filename="?([^";]+)"?/i);
  return fileNameMatch?.[1] || null;
}

async function downloadBackup(path: string, fallbackFilename: string) {
  const token = localStorage.getItem("auth_token");
  const response = await fetch(`${BACKEND_URL}${path}`, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  });

  if (!response.ok) {
    const text = await response.text();
    let message = "Backup download failed";
    try {
      const data = text ? JSON.parse(text) : {};
      message = data.error || data.message || data.detail || message;
    } catch {
      if (text) message = text;
    }
    throw new Error(message);
  }

  const blob = await response.blob();
  const downloadUrl = window.URL.createObjectURL(blob);
  const link = window.document.createElement("a");
  link.href = downloadUrl;
  link.download =
    getFileNameFromDisposition(response.headers.get("Content-Disposition")) || fallbackFilename;
  window.document.body.appendChild(link);
  link.click();
  link.remove();
  window.URL.revokeObjectURL(downloadUrl);
}

export async function downloadDatabaseBackup() {
  const timestamp = new Date().toISOString().replace(/[-:T]/g, "").slice(0, 15);
  await downloadBackup("/api/backups/database", `DFS_DATABASE_${timestamp}.sql`);
}

export async function downloadMediaBackup() {
  const timestamp = new Date().toISOString().replace(/[-:T]/g, "").slice(0, 15);
  await downloadBackup("/api/backups/media", `DFS_MEDIA_${timestamp}.zip`);
}

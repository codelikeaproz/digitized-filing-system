/**
 * BackupManagementPage — admin-only database and media backup downloads.
 */
import { useState } from "react";
import { Database, Download, HardDriveDownload, Loader2 } from "lucide-react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { downloadDatabaseBackup, downloadMediaBackup } from "@/lib/backup";

export default function BackupManagementPage() {
  const [isDatabaseDownloading, setIsDatabaseDownloading] = useState(false);
  const [isMediaDownloading, setIsMediaDownloading] = useState(false);

  const handleDatabaseDownload = async () => {
    setIsDatabaseDownloading(true);
    try {
      await downloadDatabaseBackup();
      toast.success("Database backup downloaded");
    } catch (error: unknown) {
      const message = error instanceof Error ? error.message : "Failed to download database backup";
      toast.error(message);
    } finally {
      setIsDatabaseDownloading(false);
    }
  };

  const handleMediaDownload = async () => {
    setIsMediaDownloading(true);
    try {
      await downloadMediaBackup();
      toast.success("Media backup downloaded");
    } catch (error: unknown) {
      const message = error instanceof Error ? error.message : "Failed to download media backup";
      toast.error(message);
    } finally {
      setIsMediaDownloading(false);
    }
  };

  return (
    <div className="w-full max-w-4xl space-y-6">
      <div>
        <h1 className="text-3xl font-bold flex items-center gap-3 text-gray-900">
          <HardDriveDownload className="h-8 w-8 text-[#0A4D27]" />
          Backup Management
        </h1>
        <p className="text-gray-500 mt-1">
          Download complete database and uploaded file backups for recovery or migration.
        </p>
      </div>

      <Card className="rounded-2xl border-gray-100 shadow-sm">
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-xl">
            <Database className="h-5 w-5 text-[#0A4D27]" />
            Database Backup
          </CardTitle>
          <CardDescription>
            Exports the complete DFS database, including documents, requisitioners, users, office
            units, categories, audit logs, and all system records. Output format:{" "}
            <span className="font-mono text-xs">DFS_DATABASE_YYYYMMDD_HHMMSS.sql</span>
          </CardDescription>
        </CardHeader>
        <CardContent>
          <Button
            onClick={handleDatabaseDownload}
            disabled={isDatabaseDownloading || isMediaDownloading}
            className="bg-[#0A4D27] hover:bg-[#083E1D] text-white gap-2 h-11 px-6 rounded-xl"
          >
            {isDatabaseDownloading ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Download className="h-4 w-4" />
            )}
            Download Database Backup
          </Button>
        </CardContent>
      </Card>

      <Card className="rounded-2xl border-gray-100 shadow-sm">
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-xl">
            <HardDriveDownload className="h-5 w-5 text-[#0A4D27]" />
            Media Files Backup
          </CardTitle>
          <CardDescription>
            Exports all uploaded document files and profile images from media storage. Output
            format: <span className="font-mono text-xs">DFS_MEDIA_YYYYMMDD_HHMMSS.zip</span>
          </CardDescription>
        </CardHeader>
        <CardContent>
          <Button
            onClick={handleMediaDownload}
            disabled={isDatabaseDownloading || isMediaDownloading}
            className="bg-[#0A4D27] hover:bg-[#083E1D] text-white gap-2 h-11 px-6 rounded-xl"
          >
            {isMediaDownloading ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Download className="h-4 w-4" />
            )}
            Download Media Backup
          </Button>
        </CardContent>
      </Card>
    </div>
  );
}

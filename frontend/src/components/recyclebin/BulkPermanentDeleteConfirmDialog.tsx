import React, { useEffect, useMemo, useState } from "react";
import { Trash2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { api } from "@/lib/api";
import { getBulkPermanentDeleteConfirmationPhrase } from "@/lib/permanent-delete";
import { formatStorageMbWithGb } from "@/lib/storage";

export type BulkDeleteItem = {
  type: "document" | "folder";
  id: string;
};

type BulkSummaryResponse = {
  document_count: number;
  folder_count: number;
  total_items: number;
  total_bytes: number;
  total_storage_mb: number;
  org_unit_names: string[];
};

type BulkPermanentDeleteConfirmDialogProps = {
  open: boolean;
  items: BulkDeleteItem[];
  isProcessing: boolean;
  onCancel: () => void;
  onConfirm: (confirmation: string) => void;
};

export function BulkPermanentDeleteConfirmDialog({
  open,
  items,
  isProcessing,
  onCancel,
  onConfirm,
}: BulkPermanentDeleteConfirmDialogProps) {
  const [confirmationInput, setConfirmationInput] = useState("");
  const [summary, setSummary] = useState<BulkSummaryResponse | null>(null);
  const [isLoadingSummary, setIsLoadingSummary] = useState(false);

  const requiredPhrase = useMemo(
    () => getBulkPermanentDeleteConfirmationPhrase(items.length),
    [items.length]
  );
  const isMatch = confirmationInput === requiredPhrase;
  const showMismatchError = confirmationInput.length > 0 && !isMatch;

  useEffect(() => {
    if (!open) {
      setConfirmationInput("");
      setSummary(null);
      return;
    }

    const fetchSummary = async () => {
      setIsLoadingSummary(true);
      try {
        const data = await api.post<BulkSummaryResponse>("/api/recycle-bin/bulk-summary", {
          items,
        });
        setSummary(data);
      } catch {
        setSummary(null);
      } finally {
        setIsLoadingSummary(false);
      }
    };

    fetchSummary();
  }, [open, items]);

  const documentCount = summary?.document_count ?? items.filter((item) => item.type === "document").length;
  const folderCount = summary?.folder_count ?? items.filter((item) => item.type === "folder").length;
  const totalItems = summary?.total_items ?? items.length;

  return (
    <Dialog open={open} onOpenChange={(nextOpen) => !nextOpen && onCancel()}>
      <DialogContent className="sm:max-w-md" showCloseButton={!isProcessing}>
        <DialogHeader>
          <DialogTitle className="text-destructive flex items-center gap-2">
            <Trash2 className="h-5 w-5" />
            Permanently Delete Selected Items
          </DialogTitle>
          <DialogDescription asChild>
            <div className="space-y-3 text-sm text-muted-foreground">
              <p>You are about to permanently delete:</p>
              <p>
                Documents: <span className="font-semibold text-foreground">{documentCount}</span>
              </p>
              <p>
                Folders: <span className="font-semibold text-foreground">{folderCount}</span>
              </p>
              <p>
                Total Selected:{" "}
                <span className="font-semibold text-foreground">{totalItems} Items</span>
              </p>
              <p>
                Total Storage:{" "}
                <span className="font-semibold text-foreground">
                  {isLoadingSummary
                    ? "Calculating..."
                    : summary
                      ? formatStorageMbWithGb(summary.total_storage_mb)
                      : "Unavailable"}
                </span>
              </p>
              <p>This action cannot be undone.</p>
              <div className="space-y-1">
                <p>To confirm, type:</p>
                <p className="rounded-md border bg-muted/40 px-3 py-2 font-mono text-sm text-foreground">
                  {requiredPhrase}
                </p>
              </div>
            </div>
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-2">
          <Label htmlFor="bulk-permanent-delete-confirmation">Confirmation</Label>
          <Input
            id="bulk-permanent-delete-confirmation"
            value={confirmationInput}
            onChange={(event) => setConfirmationInput(event.target.value)}
            placeholder={requiredPhrase}
            disabled={isProcessing}
            autoComplete="off"
            spellCheck={false}
          />
          {showMismatchError ? (
            <p className="text-sm text-destructive">
              Invalid confirmation text. Please type the required confirmation exactly as shown.
            </p>
          ) : null}
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={onCancel} disabled={isProcessing}>
            Cancel
          </Button>
          <Button
            variant="destructive"
            onClick={() => onConfirm(confirmationInput)}
            disabled={!isMatch || isProcessing || isLoadingSummary}
          >
            {isProcessing ? "Deleting..." : "Delete Permanently"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

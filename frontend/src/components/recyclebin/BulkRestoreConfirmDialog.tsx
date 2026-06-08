import React from "react";
import { RefreshCcw } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";

type BulkRestoreConfirmDialogProps = {
  open: boolean;
  documentCount: number;
  folderCount: number;
  totalItems: number;
  isProcessing: boolean;
  onCancel: () => void;
  onConfirm: () => void;
};

export function BulkRestoreConfirmDialog({
  open,
  documentCount,
  folderCount,
  totalItems,
  isProcessing,
  onCancel,
  onConfirm,
}: BulkRestoreConfirmDialogProps) {
  return (
    <Dialog open={open} onOpenChange={(nextOpen) => !nextOpen && onCancel()}>
      <DialogContent className="sm:max-w-md" showCloseButton={!isProcessing}>
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <RefreshCcw className="h-5 w-5" />
            Restore Selected Items
          </DialogTitle>
          <DialogDescription asChild>
            <div className="space-y-2 text-sm text-muted-foreground">
              <p>Documents: <span className="font-semibold text-foreground">{documentCount}</span></p>
              <p>Folders: <span className="font-semibold text-foreground">{folderCount}</span></p>
              <p>
                Total Selected:{" "}
                <span className="font-semibold text-foreground">{totalItems} Items</span>
              </p>
            </div>
          </DialogDescription>
        </DialogHeader>
        <DialogFooter>
          <Button variant="outline" onClick={onCancel} disabled={isProcessing}>
            Cancel
          </Button>
          <Button
            onClick={onConfirm}
            disabled={isProcessing}
            className="bg-brand-green hover:bg-brand-green/90"
          >
            {isProcessing ? "Restoring..." : "Restore Selected"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

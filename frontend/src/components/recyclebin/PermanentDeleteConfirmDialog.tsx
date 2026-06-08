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
import { getPermanentDeleteConfirmationPhrase } from "@/lib/permanent-delete";

export type PermanentDeleteItem = {
  id: string;
  type: "document" | "folder";
  name?: string;
  title?: string;
};

type PermanentDeleteConfirmDialogProps = {
  open: boolean;
  item: PermanentDeleteItem | null;
  isProcessing: boolean;
  onCancel: () => void;
  onConfirm: (confirmation: string) => void;
};

export function PermanentDeleteConfirmDialog({
  open,
  item,
  isProcessing,
  onCancel,
  onConfirm,
}: PermanentDeleteConfirmDialogProps) {
  const [confirmationInput, setConfirmationInput] = useState("");

  const displayName = item?.name || item?.title || "";
  const requiredPhrase = useMemo(
    () => (displayName ? getPermanentDeleteConfirmationPhrase(displayName) : ""),
    [displayName]
  );
  const isMatch = confirmationInput === requiredPhrase;
  const showMismatchError =
    confirmationInput.length > 0 && !isMatch;

  useEffect(() => {
    if (!open) {
      setConfirmationInput("");
    }
  }, [open, item?.id, item?.type]);

  const title =
    item?.type === "folder"
      ? "Permanently Delete Folder"
      : "Permanently Delete Document";

  return (
    <Dialog open={open} onOpenChange={(nextOpen) => !nextOpen && onCancel()}>
      <DialogContent className="sm:max-w-md" showCloseButton={!isProcessing}>
        <DialogHeader>
          <DialogTitle className="text-destructive flex items-center gap-2">
            <Trash2 className="h-5 w-5" />
            {title}
          </DialogTitle>
          <DialogDescription asChild>
            <div className="space-y-3 text-sm text-muted-foreground">
              <p>You are about to permanently delete:</p>
              <p className="font-semibold text-foreground">{displayName}</p>
              <p>
                This action cannot be undone. The{" "}
                {item?.type === "folder" ? "folder and its associated files" : "document and its associated files"}{" "}
                will be permanently removed from storage.
              </p>
              {item?.type === "folder" ? (
                <p className="font-medium text-foreground">
                  All documents inside this folder will also be permanently deleted.
                </p>
              ) : null}
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
          <Label htmlFor="permanent-delete-confirmation">Confirmation</Label>
          <Input
            id="permanent-delete-confirmation"
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
            disabled={!isMatch || isProcessing}
          >
            {isProcessing ? "Deleting..." : "Delete Permanently"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

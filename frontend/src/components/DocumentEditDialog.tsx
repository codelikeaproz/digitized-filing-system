import { useEffect, useMemo, useState } from "react";
import { FileText, FolderOpen, Hash, Loader2, MessageSquare, Tag, X } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { CategorySelect } from "@/components/CategorySelect";
import { RequisitionersEditor } from "@/components/documents/RequisitionersEditor";
import { api } from "@/lib/api";
import {
  type RequisitionerInput,
  type RequisitionerRowErrors,
  seedRequisitionersFromDocument,
  serializeRequisitionersForApi,
  validateRequisitioners,
} from "@/lib/requisitioner";
import { cn, compareByNaturalName } from "@/lib/utils";
import { Document, Folder } from "@/types";

const DOCUMENT_CODE_PATTERN = /^[A-Za-z0-9-]+$/;

type DocumentEditDialogProps = {
  open: boolean;
  document: Document | null;
  onOpenChange: (open: boolean) => void;
  onSaved?: () => void;
};

export function DocumentEditDialog({ open, document, onOpenChange, onSaved }: DocumentEditDialogProps) {
  const [folders, setFolders] = useState<Folder[]>([]);
  const [targetFolderId, setTargetFolderId] = useState("");
  const [customFileName, setCustomFileName] = useState("");
  const [docCode, setDocCode] = useState("");
  const [docCodeError, setDocCodeError] = useState("");
  const [requisitioners, setRequisitioners] = useState<RequisitionerInput[]>([]);
  const [requisitionerErrors, setRequisitionerErrors] = useState<RequisitionerRowErrors[]>([]);
  const [requisitionerListError, setRequisitionerListError] = useState("");
  const [description, setDescription] = useState("");
  const [categoryId, setCategoryId] = useState("");
  const [keywords, setKeywords] = useState<string[]>([]);
  const [keywordInput, setKeywordInput] = useState("");
  const [isSaving, setIsSaving] = useState(false);

  const trimmedDocCode = docCode.trim();
  const isDocumentCodeValid = !trimmedDocCode || DOCUMENT_CODE_PATTERN.test(trimmedDocCode);
  const documentCodeInlineError =
    docCodeError || (!isDocumentCodeValid ? "Document Code can contain letters, numbers, and hyphens only." : "");

  const folderPaths = useMemo(() => {
    const getPath = (folderId: string): string => {
      const path: string[] = [];
      let current = folders.find((folder) => folder.id === folderId);
      while (current) {
        path.unshift(current.name);
        current = folders.find((folder) => folder.id === current?.parentId);
      }
      return path.join(" > ") || "Root";
    };

    return folders
      .map((folder) => ({
        id: folder.id,
        path: getPath(folder.id),
        level: getPath(folder.id).split(" > ").length - 1,
        orgUnitId: folder.orgUnitId,
      }))
      .sort((a, b) => compareByNaturalName(a.path, b.path));
  }, [folders]);

  useEffect(() => {
    if (!open) return;
    api.get<Folder[]>("/api/folders").then(setFolders).catch(() => {
      toast.error("Failed to load folders");
    });
  }, [open]);

  useEffect(() => {
    if (!open || !document) return;
    const currentName = document.title || document.file_name || "";
    setTargetFolderId(String(document.folderId || ""));
    setCustomFileName(currentName.replace(/\.pdf$/i, ""));
    setDocCode(document.code || "");
    setDocCodeError("");
    setRequisitioners(seedRequisitionersFromDocument(document));
    setRequisitionerErrors([]);
    setRequisitionerListError("");
    setDescription(document.description || "");
    setCategoryId(String(document.categoryId || ""));
    setKeywords(Array.isArray(document.keywords) ? [...document.keywords] : []);
    setKeywordInput("");
  }, [open, document]);

  const addKeyword = () => {
    const value = keywordInput.trim();
    if (value && !keywords.includes(value)) {
      setKeywords([...keywords, value]);
      setKeywordInput("");
    }
  };

  const removeKeyword = (tag: string) => {
    setKeywords(keywords.filter((keyword) => keyword !== tag));
  };

  const handleSave = async () => {
    if (!document) return;
    if (!trimmedDocCode) {
      setDocCodeError("Document Code is required.");
      return;
    }
    if (!DOCUMENT_CODE_PATTERN.test(trimmedDocCode)) {
      setDocCodeError("Document Code can contain letters, numbers, and hyphens only.");
      return;
    }
    if (!targetFolderId) {
      toast.error("Target folder is required.");
      return;
    }
    if (!customFileName.trim()) {
      toast.error("File name is required.");
      return;
    }
    if (!categoryId) {
      toast.error("Category is required.");
      return;
    }
    if (keywords.length === 0) {
      toast.error("Add at least one keyword before saving.");
      return;
    }

    const validation = validateRequisitioners(requisitioners);
    setRequisitionerErrors(validation.rowErrors);
    setRequisitionerListError(validation.message || "");
    if (!validation.isValid) {
      toast.error(validation.message || "Please fix requisitioner details before saving.");
      return;
    }
    setRequisitionerListError("");

    setIsSaving(true);
    try {
      await api.patch(`/api/documents/${document.id}/edit`, {
        folderId: targetFolderId,
        categoryId,
        code: trimmedDocCode,
        requisitioners: serializeRequisitionersForApi(requisitioners),
        description,
        keywords,
        file_name: customFileName.trim(),
      });
      toast.success("Document details updated");
      onSaved?.();
      onOpenChange(false);
    } catch (error: any) {
      const message = error.message || "Update failed.";
      if (message.toLowerCase().includes("document code")) {
        setDocCodeError(message);
      } else {
        toast.error(message);
      }
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={(nextOpen) => !isSaving && onOpenChange(nextOpen)}>
      <DialogContent className="max-h-[90vh] overflow-y-auto sm:max-w-[640px]">
        <DialogHeader>
          <DialogTitle>Edit Document Details</DialogTitle>
          <DialogDescription>
            Update filing location, metadata, and keywords. The PDF file itself is not replaced here.
          </DialogDescription>
        </DialogHeader>

        {document && (
          <div className="space-y-4 py-2">
            <div className="bg-muted/30 border rounded-lg p-3 flex items-center gap-3">
              <FileText className="h-10 w-10 text-primary" />
              <div className="flex-1 min-w-0">
                <Label className="text-[10px] uppercase font-bold text-muted-foreground tracking-wider">
                  Current Document
                </Label>
                <p className="text-sm font-semibold truncate">{document.title || document.file_name}</p>
                <p className="text-[10px] text-muted-foreground uppercase">{document.filePath}</p>
              </div>
            </div>

            <div className="space-y-2">
              <Label className="flex items-center gap-2 text-xs font-semibold uppercase text-muted-foreground">
                <FolderOpen className="h-3.5 w-3.5" />
                Target Folder (Physical Location)
              </Label>
              <Select value={targetFolderId} onValueChange={(value) => value !== null && setTargetFolderId(value)}>
                <SelectTrigger className="h-10 text-sm w-full">
                  <SelectValue placeholder="Select destination folder...">
                    {folderPaths.find((folder) => folder.id === targetFolderId)?.path}
                  </SelectValue>
                </SelectTrigger>
                <SelectContent className="max-h-60">
                  {folderPaths.map((folder) => (
                    <SelectItem key={folder.id} value={folder.id}>
                      <span style={{ paddingLeft: `${folder.level * 12}px` }}>{folder.path}</span>
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="edit-file-name" className="text-xs font-semibold uppercase text-muted-foreground">
                  File Name
                </Label>
                <div className="flex items-center">
                  <Input
                    id="edit-file-name"
                    value={customFileName}
                    onChange={(event) => setCustomFileName(event.target.value)}
                    className="rounded-r-none h-10"
                  />
                  <div className="bg-muted px-3 h-10 flex items-center border border-l-0 rounded-r-md text-sm font-medium text-muted-foreground">
                    .pdf
                  </div>
                </div>
              </div>

              <div className="space-y-2">
                <Label htmlFor="edit-doc-code" className="flex items-center gap-2 text-xs font-semibold uppercase text-muted-foreground">
                  <Hash className="h-3.5 w-3.5" />
                  Document Code <span className="text-destructive">*</span>
                </Label>
                <Input
                  id="edit-doc-code"
                  value={docCode}
                  onChange={(event) => {
                    setDocCode(event.target.value.toUpperCase());
                    setDocCodeError("");
                  }}
                  className={cn("h-10", documentCodeInlineError && "border-destructive focus-visible:ring-destructive")}
                />
                {documentCodeInlineError && (
                  <p className="text-[11px] text-destructive font-medium">{documentCodeInlineError}</p>
                )}
              </div>
            </div>

            <RequisitionersEditor
              value={requisitioners}
              onChange={(nextValue) => {
                setRequisitioners(nextValue);
                setRequisitionerErrors([]);
                setRequisitionerListError("");
              }}
              rowErrors={requisitionerErrors}
              listError={requisitionerListError}
              disabled={isSaving}
            />

            <div className="space-y-2">
              <div className="flex justify-between items-center">
                <Label htmlFor="edit-description" className="flex items-center gap-2 text-xs font-semibold uppercase text-muted-foreground">
                  <MessageSquare className="h-3.5 w-3.5" />
                  Short Description
                </Label>
                <span className={cn("text-[10px] font-bold", description.length >= 50 ? "text-destructive" : "text-muted-foreground")}>
                  {description.length}/50
                </span>
              </div>
              <Textarea
                id="edit-description"
                value={description}
                onChange={(event) => setDescription(event.target.value.slice(0, 50))}
                className="resize-none h-20 min-h-[80px]"
              />
            </div>

            <div className="space-y-2">
              <Label className="text-xs font-semibold uppercase text-muted-foreground">Classification Category</Label>
              <CategorySelect
                value={categoryId}
                onValueChange={setCategoryId}
                className="w-full"
                orgUnitId={folderPaths.find((folder) => folder.id === targetFolderId)?.orgUnitId ?? undefined}
              />
            </div>

            <div className="space-y-3">
              <Label htmlFor="edit-keywords" className="flex items-center gap-2 text-xs font-semibold uppercase text-muted-foreground">
                <Tag className="h-3.5 w-3.5" />
                Keywords / Tags <span className="text-destructive">*</span>
              </Label>
              <div className="flex gap-2">
                <Input
                  id="edit-keywords"
                  placeholder="Add keyword and press Enter..."
                  value={keywordInput}
                  onChange={(event) => setKeywordInput(event.target.value)}
                  onKeyDown={(event) => {
                    if (event.key === "Enter") {
                      event.preventDefault();
                      addKeyword();
                    }
                  }}
                  className="h-10 flex-1"
                />
                <Button type="button" variant="secondary" onClick={addKeyword} className="shrink-0 h-10 px-4">
                  Add
                </Button>
              </div>
              <div className="flex flex-wrap gap-1.5 pt-1 min-h-[24px]">
                {keywords.length > 0 ? (
                  keywords.map((keyword) => (
                    <span
                      key={keyword}
                      className="px-2.5 py-1 gap-1.5 flex items-center bg-secondary text-secondary-foreground rounded-md text-[10px] font-bold uppercase border border-border shadow-sm"
                    >
                      {keyword}
                      <X className="h-3 w-3 cursor-pointer hover:text-destructive transition-colors" onClick={() => removeKeyword(keyword)} />
                    </span>
                  ))
                ) : (
                  <p className="text-[10px] text-amber-700 italic">Add at least one keyword (required).</p>
                )}
              </div>
            </div>
          </div>
        )}

        <DialogFooter>
          <Button variant="ghost" onClick={() => onOpenChange(false)} disabled={isSaving}>
            Cancel
          </Button>
          <Button
            onClick={handleSave}
            disabled={
              isSaving ||
              !targetFolderId ||
              !categoryId ||
              !trimmedDocCode ||
              !isDocumentCodeValid ||
              keywords.length === 0
            }
            className="bg-[#0A4D27] hover:bg-[#083E1D] text-white min-w-32"
          >
            {isSaving ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Saving...
              </>
            ) : (
              "Save Changes"
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

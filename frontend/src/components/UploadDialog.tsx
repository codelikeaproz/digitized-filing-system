/**
 * UploadDialog — PDF upload modal.
 *
 * Supports manual PDF upload via POST /api/documents/upload (multipart).
 * Validates category, folder, requisitioners, and metadata before submit.
 * Document code is auto-generated server-side from the selected category.
 */
import React, { useState, useCallback, useEffect, useMemo } from "react";
import { useDropzone } from "react-dropzone";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
  DialogDescription,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  UploadCloud,
  FileText,
  X,
  CheckCircle2,
  Loader2,
  Hash,
  MessageSquare,
  Tag,
  FolderOpen,
} from "lucide-react";
import { CategorySelect } from "@/components/CategorySelect";
import { RequisitionersEditor } from "@/components/documents/RequisitionersEditor";
import { cn, compareByNaturalName } from "@/lib/utils";
import {
  serializeRequisitionersForApi,
  type RequisitionerInput,
  type RequisitionerRowErrors,
  validateRequisitioners,
} from "@/lib/requisitioner";
import { useAuth } from "@/lib/auth-context";
import { useCategories } from "@/contexts/CategoryContext";
import { toast } from "sonner";
import { api } from "@/lib/api";
import { fetchSystemSettings, formatUploadSizeError } from "@/lib/system-settings";
import { Folder } from "@/types";

interface UploadDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  selectedFolderId?: string;
  selectedFolderPath?: string;
  storageQuotaExceeded?: boolean;
}

type WorkflowState = "manual-upload" | "category-entry" | "success";

export function UploadDialog({ open, onOpenChange, selectedFolderId, storageQuotaExceeded = false }: UploadDialogProps) {
  const { user } = useAuth();
  const { categories } = useCategories();

  const [state, setState] = useState<WorkflowState>("manual-upload");
  const [file, setFile] = useState<File | null>(null);
  const [customFileName, setCustomFileName] = useState("");
  const [docCode, setDocCode] = useState("");
  const [docCodeError, setDocCodeError] = useState("");
  const [isLoadingDocCode, setIsLoadingDocCode] = useState(false);
  const [requisitioners, setRequisitioners] = useState<RequisitionerInput[]>([]);
  const [requisitionerErrors, setRequisitionerErrors] = useState<RequisitionerRowErrors[]>([]);
  const [requisitionerListError, setRequisitionerListError] = useState("");
  const [description, setDescription] = useState("");
  const [categoryId, setCategoryId] = useState("");
  const [keywords, setKeywords] = useState<string[]>([]);
  const [keywordInput, setKeywordInput] = useState("");
  const [targetFolderId, setTargetFolderId] = useState("");
  const [folders, setFolders] = useState<Folder[]>([]);
  const [isProcessing, setIsProcessing] = useState(false);
  const [uploadLimitMb, setUploadLimitMb] = useState(15);

  const uploadLimitBytes = uploadLimitMb * 1024 * 1024;

  const reset = () => {
    setState("manual-upload");
    setFile(null);
    setCustomFileName("");
    setDocCode("");
    setDocCodeError("");
    setIsLoadingDocCode(false);
    setRequisitioners([]);
    setRequisitionerErrors([]);
    setRequisitionerListError("");
    setDescription("");
    setCategoryId("");
    setKeywords([]);
    setKeywordInput("");
    setTargetFolderId(selectedFolderId || "");
    setIsProcessing(false);
  };

  useEffect(() => {
    if (!open) {
      reset();
    } else {
      setTargetFolderId(selectedFolderId || "");
      fetchFolders();
      fetchSystemSettings()
        .then((settings) => setUploadLimitMb(settings.uploadLimitMb))
        .catch(() => setUploadLimitMb(15));
      if (storageQuotaExceeded) {
        toast.error("Storage quota exceeded. Please contact your system administrator.");
      }
    }
  }, [open, selectedFolderId, storageQuotaExceeded]);

  useEffect(() => {
    if (!categoryId) {
      setDocCode("");
      setDocCodeError("");
      return;
    }

    let cancelled = false;
    setIsLoadingDocCode(true);
    setDocCodeError("");

    api
      .get<{ code: string }>("/api/documents/next-code", { categoryId })
      .then((response) => {
        if (!cancelled) {
          setDocCode(response.code);
        }
      })
      .catch((error: any) => {
        if (!cancelled) {
          setDocCode("");
          setDocCodeError(error.message || "Unable to preview document code.");
        }
      })
      .finally(() => {
        if (!cancelled) {
          setIsLoadingDocCode(false);
        }
      });

    return () => {
      cancelled = true;
    };
  }, [categoryId]);

  const fetchFolders = async () => {
    try {
      const folderList = await api.get<Folder[]>("/api/folders");
      setFolders(folderList);
    } catch (error) {
      console.error("Failed to load folders:", error);
    }
  };

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
      }))
      .sort((a, b) => compareByNaturalName(a.path, b.path));
  }, [folders]);

  const onDrop = useCallback(
    (acceptedFiles: File[]) => {
      if (storageQuotaExceeded) {
        toast.error("Storage quota exceeded. Please contact your system administrator.");
        return;
      }
      if (acceptedFiles.length > 0) {
        const selectedFile = acceptedFiles[0];
        if (selectedFile.type !== "application/pdf") {
          toast.error("Invalid file type. Only PDF files are allowed.");
          return;
        }
        if (selectedFile.size > uploadLimitBytes) {
          toast.error(formatUploadSizeError(uploadLimitMb));
          return;
        }
        const baseName = selectedFile.name.replace(/\.[^/.]+$/, "");
        setFile(selectedFile);
        setCustomFileName(baseName);
        setState("category-entry");
      }
    },
    [storageQuotaExceeded, uploadLimitBytes, uploadLimitMb]
  );

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: { "application/pdf": [".pdf"] },
    maxFiles: 1,
    multiple: false,
    maxSize: uploadLimitBytes,
    disabled: storageQuotaExceeded,
  } as any);

  const addKeyword = () => {
    if (keywordInput.trim() && !keywords.includes(keywordInput.trim())) {
      setKeywords([...keywords, keywordInput.trim()]);
      setKeywordInput("");
    }
  };

  const removeKeyword = (tag: string) => {
    setKeywords(keywords.filter((keyword) => keyword !== tag));
  };

  const handleSave = async () => {
    if (storageQuotaExceeded) {
      toast.error("Storage quota exceeded. Please contact your system administrator.");
      return;
    }
    if (!file) {
      toast.error("File is missing.");
      return;
    }
    if (file.size > uploadLimitBytes) {
      toast.error(formatUploadSizeError(uploadLimitMb));
      return;
    }
    if (!categoryId) {
      toast.error("Category is required.");
      return;
    }
    if (!docCode.trim()) {
      setDocCodeError("Select a category with a valid code to generate a document code.");
      return;
    }
    if (!targetFolderId) {
      toast.error("Target folder is required.");
      return;
    }
    if (keywords.length === 0) {
      toast.error("Add at least one keyword before saving.");
      return;
    }
    if (!user) {
      toast.error("Auth session expired.");
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

    setIsProcessing(true);
    const cleanFileName = customFileName.trim();
    const finalName = cleanFileName ? `${cleanFileName}.pdf` : "unnamed_document.pdf";

    try {
      const physicalLocation = folderPaths.find((path) => path.id === targetFolderId)?.path || "All Files";
      const categoryObj = Array.isArray(categories) ? categories.find((category) => category.id === categoryId) : null;
      if (!categoryObj) {
        toast.error("Selected category is no longer available. Please select another category.");
        return;
      }

      const formData = new FormData();
      formData.append("file", file);
      formData.append("title", finalName);
      formData.append("requisitioners", JSON.stringify(serializeRequisitionersForApi(requisitioners)));
      formData.append("categoryId", categoryId);
      formData.append("categoryName", categoryObj.name);
      formData.append("folderId", targetFolderId);
      formData.append("uploaderId", user.id);
      formData.append("filePath", physicalLocation);
      formData.append("source", "Uploaded");
      formData.append("description", description);
      formData.append("keywords", JSON.stringify(keywords));

      await api.upload("/api/documents/upload", formData);

      setState("success");
      toast.success("Document uploaded successfully");
      setTimeout(() => onOpenChange(false), 2000);
    } catch (error: any) {
      console.error("Upload Error:", error);
      const message = error.message || "Upload failed.";
      if (message.toLowerCase().includes("document code")) {
        setDocCodeError(message);
      } else {
        toast.error(message);
      }
    } finally {
      setIsProcessing(false);
    }
  };

  const shouldPreventAccidentalClose = state === "category-entry" || state === "manual-upload" || isProcessing;

  const handleDialogOpenChange = (nextOpen: boolean, eventDetails?: { reason?: string }) => {
    if (
      !nextOpen &&
      shouldPreventAccidentalClose &&
      eventDetails?.reason &&
      eventDetails.reason !== "close-press"
    ) {
      toast.info("Use Cancel or Close to exit this form.");
      return;
    }
    onOpenChange(nextOpen);
  };

  return (
    <Dialog open={open} onOpenChange={handleDialogOpenChange} disablePointerDismissal={shouldPreventAccidentalClose}>
      <DialogContent className="sm:max-w-[600px] max-h-[90vh] overflow-y-auto" showCloseButton={!isProcessing}>
        <DialogHeader>
          <DialogTitle>
            {state === "manual-upload" && "Upload Document"}
            {state === "category-entry" && "Document Metadata"}
            {state === "success" && "Filing Complete"}
          </DialogTitle>
          {state === "category-entry" && (
            <DialogDescription>Enter document details and keywords for easier search.</DialogDescription>
          )}
        </DialogHeader>

        <div className="py-2">
          {state === "manual-upload" && (
            <div
              {...getRootProps()}
              className={cn(
                "border-2 border-dashed rounded-xl p-16 flex flex-col items-center justify-center gap-6 transition-colors cursor-pointer my-4",
                isDragActive
                  ? "border-primary bg-primary/5"
                  : "border-muted-foreground/25 hover:border-primary/50 hover:bg-muted/20"
              )}
            >
              <input {...getInputProps()} />
              <UploadCloud
                className={cn(
                  "h-16 w-16 transition-colors",
                  isDragActive ? "text-primary" : "text-muted-foreground/60"
                )}
              />
              <div className="text-center space-y-1">
                <p className="font-semibold text-xl">
                  {isDragActive ? "Drop your PDF here" : "Click or drag PDF here"}
                </p>
                <p className="text-sm text-muted-foreground">
                  Only PDF files are accepted — maximum {uploadLimitMb} MB
                </p>
                {storageQuotaExceeded ? (
                  <p className="text-sm font-medium text-destructive">
                    Storage quota exceeded. Please contact your system administrator.
                  </p>
                ) : null}
              </div>
            </div>
          )}

          {state === "category-entry" && (
            <div className="space-y-4 pb-4">
              <div className="bg-muted/30 border rounded-lg p-3 flex items-center gap-3">
                <FileText className="h-10 w-10 text-primary" />
                <div className="flex-1 min-w-0">
                  <Label className="text-[10px] uppercase font-bold text-muted-foreground tracking-wider">
                    Original Source
                  </Label>
                  <p className="text-sm font-semibold truncate">{file?.name}</p>
                  <p className="text-[10px] text-muted-foreground uppercase">
                    {(file?.size || 0) / 1024 / 1024 < 1
                      ? `${((file?.size || 0) / 1024).toFixed(1)} KB`
                      : `${((file?.size || 0) / 1024 / 1024).toFixed(1)} MB`}{" "}
                    • PDF Document
                  </p>
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

              <div className="space-y-2">
                <Label className="text-xs font-semibold uppercase text-muted-foreground">
                  Classification Category <span className="text-destructive">*</span>
                </Label>
                <CategorySelect
                  value={categoryId}
                  onValueChange={setCategoryId}
                  className="w-full"
                  orgUnitId={folders.find((folder) => folder.id === targetFolderId)?.orgUnitId ?? undefined}
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="docCode" className="flex items-center gap-2 text-xs font-semibold uppercase text-muted-foreground">
                  <Hash className="h-3.5 w-3.5" />
                  Document Code
                </Label>
                <Input
                  id="docCode"
                  value={isLoadingDocCode ? "Generating..." : docCode}
                  readOnly
                  disabled
                  placeholder="Select a category to preview"
                  className={cn("h-10 font-mono bg-muted", docCodeError && "border-destructive focus-visible:ring-destructive")}
                  aria-invalid={Boolean(docCodeError)}
                />
                {docCodeError ? (
                  <p className="text-[11px] text-destructive font-medium">{docCodeError}</p>
                ) : (
                  <p className="text-[11px] text-muted-foreground">
                    Auto-generated from category. Final code is assigned when you save.
                  </p>
                )}
              </div>

              <div className="space-y-2">
                <Label htmlFor="fileName" className="text-xs font-semibold uppercase text-muted-foreground">
                  File Name (Editable)
                </Label>
                <div className="flex w-full items-center">
                  <Input
                    id="fileName"
                    value={customFileName}
                    onChange={(event) => setCustomFileName(event.target.value)}
                    className="min-w-0 flex-1 rounded-r-none h-10"
                  />
                  <div className="shrink-0 bg-muted px-3 h-10 flex items-center border border-l-0 rounded-r-md text-sm font-medium text-muted-foreground">
                    .pdf
                  </div>
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
              />

              <div className="space-y-2">
                <div className="flex justify-between items-center">
                  <Label htmlFor="desc" className="flex items-center gap-2 text-xs font-semibold uppercase text-muted-foreground">
                    <MessageSquare className="h-3.5 w-3.5" />
                    Short Description
                  </Label>
                  <span
                    className={cn(
                      "text-[10px] font-bold",
                      description.length >= 50 ? "text-destructive" : "text-muted-foreground"
                    )}
                  >
                    {description.length}/50
                  </span>
                </div>
                <Textarea
                  id="desc"
                  placeholder="Enter a brief summary of the document..."
                  value={description}
                  onChange={(event) => setDescription(event.target.value.slice(0, 50))}
                  className="resize-none h-20 min-h-[80px]"
                />
              </div>

              <div className="space-y-3">
                <Label htmlFor="keywords" className="flex items-center gap-2 text-xs font-semibold uppercase text-muted-foreground">
                  <Tag className="h-3.5 w-3.5" />
                  Keywords / Tags <span className="text-destructive">*</span>
                </Label>
                <div className="flex gap-2">
                  <Input
                    id="keywords"
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
                        <X
                          className="h-3 w-3 cursor-pointer hover:text-destructive transition-colors"
                          onClick={() => removeKeyword(keyword)}
                        />
                      </span>
                    ))
                  ) : (
                    <p className="text-[10px] text-amber-700 italic">Add at least one keyword (required).</p>
                  )}
                </div>
              </div>
            </div>
          )}

          {state === "success" && (
            <div className="flex flex-col items-center justify-center py-10 space-y-4">
              <CheckCircle2 className="h-16 w-16 text-green-500 animate-in zoom-in duration-500" />
              <div className="text-center space-y-2">
                <p className="text-xl font-bold">Document Filed Successfully</p>
                <p className="text-sm text-muted-foreground">The metadata has been indexed and the file stored.</p>
              </div>
            </div>
          )}
        </div>

        {!isProcessing && state !== "success" && (
          <DialogFooter className="pt-2">
            <Button variant="ghost" onClick={() => handleDialogOpenChange(false)}>
              Cancel
            </Button>
            {state === "category-entry" && (
              <Button
                onClick={handleSave}
                disabled={
                  !categoryId ||
                  !targetFolderId ||
                  !docCode.trim() ||
                  isLoadingDocCode ||
                  Boolean(docCodeError) ||
                  keywords.length === 0
                }
                className="bg-[#0A4D27] hover:bg-[#083E1D] text-white min-w-32 h-10 rounded-lg"
              >
                Confirm and Save Filing
              </Button>
            )}
          </DialogFooter>
        )}

        {isProcessing && (
          <div className="flex items-center justify-center gap-3 py-4 text-primary font-medium">
            <Loader2 className="h-5 w-5 animate-spin" />
            <span>Processing and storing document...</span>
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}

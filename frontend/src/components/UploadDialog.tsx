import React, { useState, useCallback, useEffect, useMemo } from "react";
import { useDropzone } from "react-dropzone";
import { 
  Dialog, 
  DialogContent, 
  DialogHeader, 
  DialogTitle, 
  DialogFooter,
  DialogDescription
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
  SelectValue 
} from "@/components/ui/select";
import { 
  UploadCloud, 
  FileText, 
  X, 
  CheckCircle2, 
  Scan, 
  Wifi, 
  Loader2,
  AlertCircle,
  Play,
  Hash,
  MessageSquare,
  Tag,
  FolderOpen
} from "lucide-react";
import { CategorySelect } from "@/components/CategorySelect";
import { cn } from "@/lib/utils";
import { useAuth } from "@/lib/auth-context";
import { useCategories } from "@/contexts/CategoryContext";
import { toast } from "sonner";
import { logAudit } from "@/lib/audit";
import { Progress } from "@/components/ui/progress";
import { api } from "@/lib/api";
import { Folder } from "@/types";

const SCANNER_STATION_ID = import.meta.env.VITE_SCANNER_STATION_ID || "SCANNER-PC-01";
const SCANNER_STATION_LABEL = "Scanner";

interface UploadDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  selectedFolderId?: string;
  selectedFolderPath?: string;
}

type WorkflowState = 'choose' | 'detecting' | 'scanning' | 'manual-upload' | 'category-entry' | 'waiting-scan' | 'success' | 'scan-failed';

interface ScannerStation {
  stationId: string;
  name?: string;
  status: "CONNECTED" | "NOT_DETECTED" | "ERROR";
  lastSeenAt?: string | null;
  errorMessage?: string;
  watchedFolder?: string;
  isOnline?: boolean;
}

interface ScanJob {
  id: string;
  stationId: string;
  status: "PENDING" | "WAITING_FOR_SCAN" | "UPLOADING" | "COMPLETED" | "FAILED" | "CANCELLED";
  errorMessage?: string;
}

export function UploadDialog({ open, onOpenChange, selectedFolderId, selectedFolderPath }: UploadDialogProps) {
  const { user } = useAuth();
  const { categories } = useCategories();
  
  const [state, setState] = useState<WorkflowState>('choose');
  const [source, setSource] = useState<'Scanned' | 'Uploaded'>('Uploaded');
  const [file, setFile] = useState<File | null>(null);
  const [customFileName, setCustomFileName] = useState("");
  const [docCode, setDocCode] = useState("");
  const [docTitle, setDocTitle] = useState("");
  const [description, setDescription] = useState("");
  const [categoryId, setCategoryId] = useState("");
  const [keywords, setKeywords] = useState<string[]>([]);
  const [keywordInput, setKeywordInput] = useState("");
  const [targetFolderId, setTargetFolderId] = useState("");
  const [folders, setFolders] = useState<Folder[]>([]);
  const [isProcessing, setIsProcessing] = useState(false);
  const [progress, setProgress] = useState(0);
  const [scannerMessage, setScannerMessage] = useState("");
  const [scannerStatus, setScannerStatus] = useState<ScannerStation | null>(null);
  const [activeScanJob, setActiveScanJob] = useState<ScanJob | null>(null);
  const scannerOnline = Boolean(scannerStatus?.isOnline);

  const reset = () => {
    setState('choose');
    setFile(null);
    setCustomFileName("");
    setDocCode("");
    setDocTitle("");
    setDescription("");
    setCategoryId("");
    setKeywords([]);
    setKeywordInput("");
    setTargetFolderId(selectedFolderId || "");
    setIsProcessing(false);
    setProgress(0);
    setScannerMessage("");
    setActiveScanJob(null);
  };

  useEffect(() => {
    if (!open) {
      reset();
    } else {
      setTargetFolderId(selectedFolderId || "");
      fetchFolders();
      fetchScannerStatus();
    }
  }, [open, selectedFolderId]);

  useEffect(() => {
    if (!open) return;
    const interval = window.setInterval(fetchScannerStatus, 3000);
    return () => window.clearInterval(interval);
  }, [open]);

  const fetchFolders = async () => {
    try {
      const folderList = await api.get<Folder[]>("/api/folders");
      setFolders(folderList);
    } catch (error) {
      console.error("Failed to load folders:", error);
    }
  };

  const fetchScannerStatus = async () => {
    try {
      const stations = await api.get<ScannerStation[]>("/api/scanner/stations");
      setScannerStatus(stations.find(station => station.stationId === SCANNER_STATION_ID) || null);
    } catch (error) {
      console.error("Failed to load scanner status:", error);
      setScannerStatus(null);
    }
  };

  const folderPaths = useMemo(() => {
    const getPath = (folderId: string): string => {
      const path: string[] = [];
      let current = folders.find(f => f.id === folderId);
      while (current) {
        path.unshift(current.name);
        current = folders.find(f => f.id === current?.parentId);
      }
      return path.join(" > ") || "Root";
    };

    return folders.map(f => ({
      id: f.id,
      path: getPath(f.id),
      level: getPath(f.id).split(" > ").length - 1
    })).sort((a, b) => a.path.localeCompare(b.path));
  }, [folders]);

  const onDrop = useCallback((acceptedFiles: File[]) => {
    if (acceptedFiles.length > 0) {
      const selectedFile = acceptedFiles[0];
      if (selectedFile.type !== "application/pdf") {
        toast.error("Invalid file type. Only PDF files are allowed.");
        return;
      }
      const baseName = selectedFile.name.replace(/\.[^/.]+$/, "");
      setFile(selectedFile);
      setCustomFileName(baseName);
      setDocTitle(baseName);
      setState('category-entry');
      setSource('Uploaded');
    }
  }, []);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: { 'application/pdf': ['.pdf'] },
    maxFiles: 1,
    multiple: false
  } as any);

  const handleStartScan = async () => {
    setSource('Scanned');
    setFile(null);
    setCustomFileName(`SCN_${Date.now()}`);
    setDocTitle("");
    setScannerMessage(
      scannerOnline
        ? "Scanner bridge is connected. Enter metadata, then scan using Epson Scan 2."
        : "Scanner bridge has not reported as connected. You can still create a job, but the bridge must be running to upload."
    );
    setState('category-entry');
  };

  const addKeyword = () => {
    if (keywordInput.trim() && !keywords.includes(keywordInput.trim())) {
      setKeywords([...keywords, keywordInput.trim()]);
      setKeywordInput("");
    }
  };

  const removeKeyword = (tag: string) => {
    setKeywords(keywords.filter(k => k !== tag));
  };

  const handleSave = async () => {
    if (source === "Uploaded" && !file) {
      toast.error("File is missing.");
      return;
    }
    if (!docCode.trim()) {
      toast.error("Document Code is required.");
      return;
    }
    if (!categoryId) {
      toast.error("Category is required.");
      return;
    }
    if (!targetFolderId) {
      toast.error("Target folder is required.");
      return;
    }
    if (!user) {
      toast.error("Auth session expired.");
      return;
    }
    
    setIsProcessing(true);
    let cleanFileName = customFileName.trim();
    const finalName = cleanFileName ? `${cleanFileName}.pdf` : "unnamed_document.pdf";
    
    try {
      const selectedFolder = folders.find(f => f.id === targetFolderId);
      const physicalLocation = folderPaths.find(p => p.id === targetFolderId)?.path || "All Files";
      
      const categoryObj = Array.isArray(categories) ? categories.find(c => c.id === categoryId) : null;
      if (!categoryObj) {
        toast.error("Selected category is no longer available. Please select another category.");
        return;
      }

      if (source === "Scanned") {
        const scanJob = await api.post<ScanJob>("/api/scan-jobs", {
          stationId: SCANNER_STATION_ID,
          title: finalName,
          requestor: docTitle,
          categoryId,
          folderId: targetFolderId,
          code: docCode,
          description,
          keywords,
        });
        setActiveScanJob(scanJob);
        setScannerMessage("Scan job created. Use Epson Scan 2 and save the PDF to the bridge incoming folder.");
        setState("waiting-scan");
        toast.success("Scan job created. Waiting for scanned PDF.");
        return;
      }

      const formData = new FormData();
      formData.append("file", file as File);
      formData.append("title", finalName);
      formData.append("requestor", docTitle);
      formData.append("categoryId", categoryId);
      formData.append("categoryName", categoryObj.name);
      formData.append("folderId", targetFolderId);
      formData.append("uploaderId", user.id);
      formData.append("filePath", physicalLocation);
      formData.append("source", source);
      formData.append("code", docCode);
      formData.append("description", description);
      formData.append("keywords", JSON.stringify(keywords));

      await api.upload("/api/documents/upload", formData);

      await logAudit("UPLOAD", `Uploaded: ${finalName} to ${physicalLocation} [Code: ${docCode}]`);
      
      setState('success');
      toast.success("Document uploaded successfully");
      setTimeout(() => onOpenChange(false), 2000);
    } catch (error: any) {
      console.error("Upload Error:", error);
      toast.error(error.message || "Upload failed.");
    } finally {
      setIsProcessing(false);
    }
  };

  useEffect(() => {
    if (state !== "waiting-scan" || !activeScanJob) return;

    const interval = window.setInterval(async () => {
      try {
        const job = await api.get<ScanJob>(`/api/scan-jobs/${activeScanJob.id}`);
        setActiveScanJob(job);

        if (job.status === "COMPLETED") {
          setState("success");
          toast.success("Scanned document uploaded successfully");
          window.clearInterval(interval);
          setTimeout(() => onOpenChange(false), 1800);
        } else if (job.status === "FAILED" || job.status === "CANCELLED") {
          setState("scan-failed");
          setScannerMessage(job.errorMessage || "Scanner bridge failed to upload the PDF.");
          window.clearInterval(interval);
        }
      } catch (error: any) {
        console.error("Scan job polling failed:", error);
      }
    }, 2000);

    return () => window.clearInterval(interval);
  }, [state, activeScanJob?.id, onOpenChange]);

  const isScanWaiting = state === "waiting-scan";
  const shouldProtectDialogClose = isScanWaiting || isProcessing;

  const handleDialogOpenChange = (nextOpen: boolean, eventDetails?: { reason?: string }) => {
    if (
      !nextOpen
      && shouldProtectDialogClose
      && eventDetails?.reason
      && eventDetails.reason !== "close-press"
    ) {
      toast.info("Use Cancel to stop the scan job first.");
      return;
    }
    if (!nextOpen && activeScanJob && state === "waiting-scan") {
      api.patch(`/api/scan-jobs/${activeScanJob.id}`, {}).catch((error) => {
        console.error("Failed to cancel scan job:", error);
      });
    }
    onOpenChange(nextOpen);
  };

  return (
    <Dialog
      open={open}
      onOpenChange={handleDialogOpenChange}
      disablePointerDismissal={shouldProtectDialogClose}
    >
      <DialogContent
        className="sm:max-w-[600px] max-h-[90vh] overflow-y-auto"
        showCloseButton={!shouldProtectDialogClose}
      >
        <DialogHeader>
          <DialogTitle>
            {state === 'choose' && "Digitization Source"}
            {state === 'manual-upload' && "File Upload"}
            {state === 'category-entry' && "Document Metadata"}
            {state === 'waiting-scan' && "Waiting for Epson Scan"}
            {state === 'success' && "Filing Complete"}
            {state === 'scan-failed' && "Scan Failed"}
            {state === 'detecting' && "Scanner Detection"}
            {state === 'scanning' && "Digitizing..."}
          </DialogTitle>
          <DialogDescription>
            {state === 'category-entry' && "Enter document details and keywords for easier search."}
          </DialogDescription>
        </DialogHeader>

        <div className="py-2">
          {state === 'choose' && (
            <div className="space-y-4 py-4">
              <div className="flex items-center justify-between rounded-lg border bg-muted/30 px-3 py-2 text-xs">
                <span className="font-semibold text-muted-foreground">Scanner Station</span>
                <span className={cn(
                  "font-bold",
                  scannerOnline ? "text-green-700" : "text-amber-700"
                )}>
                  {SCANNER_STATION_LABEL} - {scannerOnline ? "Bridge Connected" : "Bridge Not Running"}
                </span>
              </div>
              <div className="grid grid-cols-2 gap-4">
              <Button 
                variant="outline" 
                className="h-32 flex flex-col gap-2 hover:border-primary hover:bg-primary/5"
                onClick={handleStartScan}
              >
                <Scan className="h-8 w-8 text-primary" />
                <span>Scan with Epson</span>
                <span className="text-[10px] text-muted-foreground">USB / LAN / WiFi supported</span>
              </Button>
              <Button 
                variant="outline" 
                className="h-32 flex flex-col gap-2 hover:border-primary hover:bg-primary/5"
                onClick={() => setState('manual-upload')}
              >
                <UploadCloud className="h-8 w-8 text-primary" />
                <span>Manual Upload</span>
                <span className="text-[10px] text-muted-foreground">Accepts PDF only</span>
              </Button>
              </div>
            </div>
          )}

          {state === 'detecting' && (
            <div className="flex flex-col items-center justify-center py-10 gap-4">
              <Wifi className="h-12 w-12 text-primary animate-pulse" />
              <p className="text-sm font-medium">{scannerMessage}</p>
            </div>
          )}

          {state === 'scanning' && (
            <div className="flex flex-col items-center justify-center py-10 gap-6 w-full">
              <Scan className="h-16 w-16 text-primary animate-bounce" />
              <div className="w-full space-y-2">
                <div className="flex justify-between text-xs font-medium">
                  <span>Digitizing...</span>
                  <span>{progress}%</span>
                </div>
                <Progress value={progress} className="h-2" />
              </div>
            </div>
          )}

          {state === 'manual-upload' && (
            <div 
              {...getRootProps()} 
              className={cn(
                "border-2 border-dashed rounded-xl p-12 flex flex-col items-center justify-center gap-4 transition-colors cursor-pointer",
                isDragActive ? "border-primary bg-primary/5" : "border-muted-foreground/25 hover:border-primary/50"
              )}
            >
              <input {...getInputProps()} />
              <UploadCloud className="h-12 w-12 text-primary" />
              <div className="text-center">
                <p className="font-semibold text-lg">Click or drag PDF here</p>
                <p className="text-sm text-muted-foreground mt-1">Maximum file size: 20MB</p>
              </div>
            </div>
          )}

          {state === 'category-entry' && (
            <div className="space-y-4 pb-4">
              {/* Row 1: Original Source (full width) */}
              {source === "Scanned" && (
                <div className="rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-900">
                  This creates a pending scan record only. Start the Scanner Bridge, then scan in Epson Scan 2 and save the PDF to the incoming folder.
                </div>
              )}
              <div className="bg-muted/30 border rounded-lg p-3 flex items-center gap-3">
                <FileText className="h-10 w-10 text-primary" />
                <div className="flex-1 min-w-0">
                  <Label className="text-[10px] uppercase font-bold text-muted-foreground tracking-wider">{source === "Scanned" ? "Scan Source" : "Original Source"}</Label>
                  <p className="text-sm font-semibold truncate">{source === "Scanned" ? "Epson Scan 2 PDF output" : file?.name}</p>
                  <p className="text-[10px] text-muted-foreground uppercase">{(file?.size || 0) / 1024 / 1024 < 1 ? `${((file?.size || 0) / 1024).toFixed(1)} KB` : `${((file?.size || 0) / 1024 / 1024).toFixed(1)} MB`} • PDF Document</p>
                </div>
              </div>

              {/* Row 2: Target Folder (full width) */}
              <div className="space-y-2">
                <Label className="flex items-center gap-2 text-xs font-semibold uppercase text-muted-foreground">
                  <FolderOpen className="h-3.5 w-3.5" />
                  Target Folder (Physical Location)
                </Label>
                <Select value={targetFolderId} onValueChange={(val) => val !== null && setTargetFolderId(val)}>
                  <SelectTrigger className="h-10 text-sm w-full">
                    <SelectValue placeholder="Select destination folder...">
                      {folderPaths.find(fp => fp.id === targetFolderId)?.path}
                    </SelectValue>
                  </SelectTrigger>
                  <SelectContent>
                    {folderPaths.map(fp => (
                      <SelectItem key={fp.id} value={fp.id}>
                        <span style={{ paddingLeft: `${fp.level * 12}px` }}>
                          {fp.path}
                        </span>
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              {/* Row 3: File Name (left) | Document Code (right) */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="fileName" className="text-xs font-semibold uppercase text-muted-foreground">File Name (Editable)</Label>
                  <div className="flex items-center">
                    <Input 
                      id="fileName" 
                      value={customFileName} 
                      onChange={(e) => setCustomFileName(e.target.value)}
                      className="rounded-r-none h-10"
                    />
                    <div className="bg-muted px-3 h-10 flex items-center border border-l-0 rounded-r-md text-sm font-medium text-muted-foreground">.pdf</div>
                  </div>
                </div>

                <div className="space-y-2">
                  <Label htmlFor="docCode" className="flex items-center gap-2 text-xs font-semibold uppercase text-muted-foreground">
                    <Hash className="h-3.5 w-3.5" />
                    Document Code <span className="text-destructive">*</span>
                  </Label>
                  <Input 
                    id="docCode" 
                    placeholder="e.g. LGL-2023-001" 
                    value={docCode} 
                    onChange={(e) => setDocCode(e.target.value)}
                    className="h-10"
                    required
                  />
                </div>
              </div>

              {/* Row 4: Title / Requestor Name (full width) */}
              <div className="space-y-2">
                <Label htmlFor="docTitle" className="text-xs font-semibold uppercase text-muted-foreground">Title / Requestor Name</Label>
                <Input 
                  id="docTitle" 
                  placeholder="Enter document title or name of requestor" 
                  value={docTitle} 
                  onChange={(e) => setDocTitle(e.target.value)}
                  className="h-10"
                />
              </div>

              {/* Row 5: Description (full width) */}
              <div className="space-y-2">
                <div className="flex justify-between items-center">
                  <Label htmlFor="desc" className="flex items-center gap-2 text-xs font-semibold uppercase text-muted-foreground">
                    <MessageSquare className="h-3.5 w-3.5" />
                    Short Description
                  </Label>
                  <span className={cn("text-[10px] font-bold", description.length >= 50 ? "text-destructive" : "text-muted-foreground")}>
                    {description.length}/50
                  </span>
                </div>
                <Textarea 
                  id="desc" 
                  placeholder="Enter a brief summary of the document..." 
                  value={description} 
                  onChange={(e) => setDescription(e.target.value.slice(0, 50))}
                  className="resize-none h-20 min-h-[80px]"
                />
              </div>

              {/* Row 6: Category (full width) */}
              <div className="space-y-2">
                <Label className="text-xs font-semibold uppercase text-muted-foreground">Classification Category</Label>
                <CategorySelect 
                  value={categoryId} 
                  onValueChange={setCategoryId}
                  className="w-full"
                  orgUnitId={folders.find((f: any) => f.id === targetFolderId)?.orgUnitId ?? undefined}
                />
              </div>

              {/* Row 7: Keywords / Tags (full width) */}
              <div className="space-y-3">
                <Label htmlFor="keywords" className="flex items-center gap-2 text-xs font-semibold uppercase text-muted-foreground">
                  <Tag className="h-3.5 w-3.5" />
                  Keywords / Tags
                </Label>
                <div className="flex gap-2">
                  <Input 
                    id="keywords" 
                    placeholder="Add keyword and press Enter..." 
                    value={keywordInput}
                    onChange={(e) => setKeywordInput(e.target.value)}
                    onKeyDown={(e) => {
                       if (e.key === 'Enter') {
                         e.preventDefault();
                         addKeyword();
                       }
                    }}
                    className="h-10 flex-1"
                  />
                  <Button type="button" variant="secondary" onClick={addKeyword} className="shrink-0 h-10 px-4">Add</Button>
                </div>
                <div className="flex flex-wrap gap-1.5 pt-1 min-h-[24px]">
                  {keywords.length > 0 ? keywords.map(kw => (
                    <span key={kw} className="px-2.5 py-1 gap-1.5 flex items-center bg-secondary text-secondary-foreground rounded-md text-[10px] font-bold uppercase border border-border shadow-sm">
                      {kw}
                      <X className="h-3 w-3 cursor-pointer hover:text-destructive transition-colors" onClick={() => removeKeyword(kw)} />
                    </span>
                  )) : (
                    <p className="text-[10px] text-muted-foreground italic">No keywords added</p>
                  )}
                </div>
              </div>
            </div>
          )}

          {state === 'waiting-scan' && (
            <div className="flex flex-col items-center justify-center py-10 gap-4 text-center">
              <Loader2 className="h-12 w-12 animate-spin text-primary" />
              <div className="space-y-2">
                <p className="text-lg font-bold">Waiting for PDF</p>
                <p className="text-sm text-muted-foreground max-w-md">
                  Scan with Epson Scan 2, then save the PDF to the incoming folder.
                </p>
                <div className="mx-auto max-w-md rounded-md border bg-muted/30 p-3 text-left text-xs text-muted-foreground">
                  <div><span className="font-semibold text-foreground">Station:</span> {SCANNER_STATION_LABEL}</div>
                  <div><span className="font-semibold text-foreground">Bridge:</span> {scannerOnline ? "Connected" : "Not detected or not sending heartbeat"}</div>
                  <div><span className="font-semibold text-foreground">Incoming folder:</span> {scannerStatus?.watchedFolder || "C:\\DFS_Scanner\\Incoming"}</div>
                  {!scannerOnline && (
                    <div className="mt-2 text-amber-700">
                      Start Scanner Bridge before scanning.
                    </div>
                  )}
                </div>
                <p className="text-xs text-muted-foreground max-w-md">
                  Keep this open. Use Cancel to stop this job.
                </p>
                <p className="text-xs font-mono text-muted-foreground">
                  Job #{activeScanJob?.id} - {activeScanJob?.status}
                </p>
              </div>
            </div>
          )}

          {state === 'scan-failed' && (
            <div className="flex flex-col items-center justify-center py-10 gap-4 text-center">
              <AlertCircle className="h-12 w-12 text-destructive" />
              <div className="space-y-2">
                <p className="text-lg font-bold">Scanner upload failed</p>
                <p className="text-sm text-muted-foreground max-w-md">
                  {scannerMessage || "Check the scanner bridge log and try scanning again."}
                </p>
              </div>
            </div>
          )}

          {state === 'success' && (
            <div className="flex flex-col items-center justify-center py-10 space-y-4">
              <CheckCircle2 className="h-16 w-16 text-green-500 animate-in zoom-in duration-500" />
              <div className="text-center space-y-2">
                <p className="text-xl font-bold">Document Filed Successfully</p>
                <p className="text-sm text-muted-foreground">The metadata has been indexed and the file stored.</p>
              </div>
            </div>
          )}
        </div>

        {!isProcessing && state !== 'success' && (
          <DialogFooter className="pt-2">
            <Button variant="ghost" onClick={() => handleDialogOpenChange(false)}>Cancel</Button>
            {state === 'category-entry' && (
              <Button 
                onClick={handleSave} 
                disabled={!categoryId || !targetFolderId || !docTitle || !docCode.trim()}
                className="bg-[#0A4D27] hover:bg-[#083E1D] text-white min-w-32 h-10 rounded-lg"
              >
                {source === "Scanned" ? "Create Scan Job" : "Confirm and Save Filing"}
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

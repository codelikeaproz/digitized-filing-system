/**
 * FolderNavigation — sidebar folder tree with create/rename/delete actions.
 *
 * Loads tree from GET /api/folders/tree. Folder mutations call folders API.
 * Delete availability depends on user role (Staff: empty folders only).
 */
import React, { useState } from "react";
import { Folder, ChevronRight, ChevronDown, Plus, MoreHorizontal, Pencil, Trash2, FolderPlus, Building2 } from "lucide-react";
import { cn, sortByNaturalName } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
  DialogDescription,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { toast } from "sonner";
import { logAudit } from "@/lib/audit";
import { useAuth } from "@/lib/auth-context";
import { api } from "@/lib/api";

const ALL_FILES_NODE = {
  id: "all-files",
  name: "All Files",
  isVirtual: true,
};

interface FolderItemProps {
  folder: any;
  level: number;
  onSelect: (folder: any) => void;
  onAddSubfolder: (folder: any) => void;
  onRename: (folder: any) => void;
  onDelete: (folder: any) => void;
  selectedId?: string;
}

const FolderItem: React.FC<FolderItemProps> = ({ 
  folder, 
  level, 
  onSelect, 
  onAddSubfolder,
  onRename,
  onDelete,
  selectedId 
}) => {
  const { user } = useAuth();
  const [isOpen, setIsOpen] = useState(false);
  const childNodes = sortByNaturalName(folder.children || folder.folders || []);
  const hasChildren = childNodes.length > 0;
  const isAdmin = user?.role === 'admin';
  const isDeptHead = user?.role === 'dept_head';
  const isStaff = user?.role === 'staff';
  const isVirtual = Boolean(folder.isVirtual || folder.is_virtual);
  const isOrgUnit = folder.type === "org_unit" || folder.isOrgUnit;
  const isFolder = folder.type === "folder" || (!isVirtual && !isOrgUnit);

  const isNonEmpty = (folder.documentCount || 0) > 0 || (folder.subfolderCount || 0) > 0;
  const canAddSubfolder = !isVirtual && (isFolder || isOrgUnit);
  const canRename = isFolder && (isAdmin || isDeptHead || isStaff);
  const canDelete = isFolder && (isAdmin || isDeptHead || (isStaff && !isNonEmpty));
  const canManage = canAddSubfolder || canRename || canDelete;

  return (
    <div className="select-none">
      <div 
        className={cn(
          "group flex items-center gap-2 rounded-md px-4 py-1.5 text-sm font-medium hover:bg-accent hover:text-accent-foreground cursor-pointer",
          selectedId === folder.id && "bg-accent text-accent-foreground"
        )}
        style={{ paddingLeft: `${level * 12 + 16}px` }}
        onClick={() => {
          onSelect(folder);
          setIsOpen(!isOpen);
        }}
      >
        <div className="flex h-4 w-4 items-center justify-center">
          {hasChildren ? (
            isOpen ? <ChevronDown className="h-3 w-3" /> : <ChevronRight className="h-3 w-3" />
          ) : null}
        </div>
        {isOrgUnit ? (
          <Building2 className={cn("h-4 w-4", selectedId === folder.id ? "text-primary" : "text-emerald-700")} />
        ) : (
          <Folder className={cn("h-4 w-4", selectedId === folder.id ? "text-primary" : "text-muted-foreground")} />
        )}
        <span className="flex-1 truncate">{folder.name}</span>
        {canManage && (
          <DropdownMenu>
            <DropdownMenuTrigger
              render={
                <Button variant="ghost" className="h-6 w-6 p-0 opacity-0 group-hover:opacity-100">
                  <MoreHorizontal className="h-3 w-3" />
                </Button>
              }
              onClick={(e) => e.stopPropagation()}
            />
            <DropdownMenuContent align="end">
              {canAddSubfolder && (
                <DropdownMenuItem className="whitespace-nowrap" onClick={(e) => { e.stopPropagation(); onAddSubfolder(folder); }}>
                  <FolderPlus className="mr-2 h-4 w-4 shrink-0" />
                  {isOrgUnit ? "New Folder" : "New Subfolder"}
                </DropdownMenuItem>
              )}
              {canRename && (
                <DropdownMenuItem onClick={(e) => { e.stopPropagation(); onRename(folder); }}>
                  <Pencil className="mr-2 h-4 w-4" />
                  Rename Folder
                </DropdownMenuItem>
              )}
              {isFolder && (
                <DropdownMenuItem 
                  className={cn("text-destructive", !canDelete && "opacity-50 cursor-not-allowed")} 
                  disabled={!canDelete}
                  onClick={(e) => { 
                    e.stopPropagation(); 
                    if (canDelete) onDelete(folder); 
                  }}
                >
                  <Trash2 className="mr-2 h-4 w-4" />
                  Delete {isNonEmpty && "(Non-Empty)"}
                </DropdownMenuItem>
              )}
            </DropdownMenuContent>
          </DropdownMenu>
        )}
      </div>
      {isOpen && hasChildren && (
        <div className="mt-1">
          {childNodes.map((child: any) => (
            <FolderItem 
              key={child.id}
              folder={child}
              level={level + 1}
              onSelect={onSelect}
              onAddSubfolder={onAddSubfolder}
              onRename={onRename}
              onDelete={onDelete}
              selectedId={selectedId}
            />
          ))}
        </div>
      )}
    </div>
  );
};

export function FolderNavigation({ folders, onSelect, selectedId }: { folders: any[], onSelect: (f: any) => void, selectedId?: string }) {
  const { user } = useAuth();
  const [dialogType, setDialogType] = useState<'create' | 'rename' | 'delete' | null>(null);
  const [targetFolder, setTargetFolder] = useState<any>(null);
  const [folderName, setFolderName] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  const findNodeById = (nodes: any[], id?: string): any | null => {
    if (!id) return null;
    for (const node of nodes) {
      if (String(node.id) === String(id)) return node;
      const found = findNodeById(node.children || node.folders || [], id);
      if (found) return found;
    }
    return null;
  };

  const handleAction = async () => {
    if ((dialogType === "create" || dialogType === "rename") && !folderName.trim()) return;
    if ((dialogType === "rename" || dialogType === "delete") && (targetFolder?.isVirtual || targetFolder?.is_virtual || targetFolder?.type === "org_unit")) return;

    setIsSubmitting(true);
    try {
      if (dialogType === "create") {
        const isParentFolder = targetFolder?.type === "folder" || (targetFolder && !targetFolder.isVirtual && !targetFolder.is_virtual && targetFolder.type !== "org_unit");
        const parentId = isParentFolder ? targetFolder.id : null;
        const orgUnitId = targetFolder?.type === "org_unit" ? targetFolder.orgUnitId : targetFolder?.orgUnitId;
        await api.post("/api/folders", {
          name: folderName.trim(),
          parentId: parentId,
          orgUnitId: orgUnitId,
          createdBy: user?.id,
        });
        await logAudit("CREATE_FOLDER", `Created folder: ${folderName}${parentId ? ` as subfolder of ${targetFolder.name}` : ""}`);
        toast.success("Folder created");
      } else if (dialogType === "rename" && targetFolder) {
        await api.patch(`/api/folders/${targetFolder.id}/rename`, {
          name: folderName.trim(),
        });
        /*
          `Renamed folder: ${targetFolder.name} → ${folderName.trim()}`,
        */
        toast.success("Folder renamed");
      } else if (dialogType === "delete" && targetFolder) {
        await api.delete(`/api/folders/${targetFolder.id}`);
        await logAudit("DELETE_FOLDER", `Deleted folder: ${targetFolder.name}`);
        toast.success("Folder deleted");
        if (selectedId === targetFolder.id) onSelect(null);
      }
      
      setDialogType(null);
      setTargetFolder(null);
      setFolderName("");
      window.location.reload(); 
    } catch (error: any) {
      console.error(`Error during folder ${dialogType}:`, error);
      toast.error(error.message || `Failed to ${dialogType} folder`);
    } finally {
      setIsSubmitting(false);
    }
  };

  const openCreate = (parent: any = null) => {
    setTargetFolder(parent?.isVirtual || parent?.is_virtual ? null : parent);
    setFolderName("");
    setDialogType('create');
  };

  const openCreateFromToolbar = () => {
    const selectedNode = findNodeById(nodes, selectedId);
    const canUseSelectedNode = selectedNode && !selectedNode.isVirtual && !selectedNode.is_virtual;

    if (canUseSelectedNode) {
      openCreate(selectedNode);
      return;
    }

    if (user?.role === "admin") {
      toast.error("Select an Org Unit first, then create a folder inside it.");
      return;
    }

    openCreate();
  };

  const openRename = (folder: any) => {
    if (folder.isVirtual || folder.is_virtual || folder.type === "org_unit") return;
    setTargetFolder(folder);
    setFolderName(folder.name);
    setDialogType('rename');
  };

  const openDelete = (folder: any) => {
    if (folder.isVirtual || folder.is_virtual || folder.type === "org_unit") return;
    setTargetFolder(folder);
    setDialogType('delete');
  };

  const baseNodes = folders.some((folder) => folder.id === ALL_FILES_NODE.id)
    ? folders
    : [ALL_FILES_NODE, ...folders];
  const nodes = [
    ...baseNodes.filter((folder) => folder.id === ALL_FILES_NODE.id),
    ...sortByNaturalName(baseNodes.filter((folder) => folder.id !== ALL_FILES_NODE.id)),
  ];

  return (
    <div className="flex h-full min-h-0 flex-col gap-4">
      <div className="flex shrink-0 items-center justify-between px-4">
        <h3 className="text-sm font-semibold text-muted-foreground uppercase tracking-wider">Folders</h3>
        <Button variant="ghost" size="icon" className="h-6 w-6" onClick={openCreateFromToolbar}>
          <Plus className="h-4 w-4" />
        </Button>
      </div>
      <div className="min-h-0 flex-1 space-y-1 overflow-y-auto overscroll-contain pr-1">
        {nodes.map((folder) => (
          <FolderItem 
            key={folder.id}
            folder={folder}
            level={0}
            onSelect={onSelect}
            onAddSubfolder={openCreate}
            onRename={openRename}
            onDelete={openDelete}
            selectedId={selectedId}
          />
        ))}
      </div>

      {/* Create/Rename Dialog */}
      <Dialog open={dialogType === 'create' || dialogType === 'rename'} onOpenChange={(open) => !open && setDialogType(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{dialogType === 'create' ? 'Create New Folder' : 'Rename Folder'}</DialogTitle>
          </DialogHeader>
          <div className="grid gap-4 py-4">
            <div className="grid gap-2">
              <Label htmlFor="name">Folder Name</Label>
              <Input
                id="name"
                placeholder="Enter folder name..."
                value={folderName}
                onChange={(e) => setFolderName(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter") handleAction();
                }}
                autoFocus
              />
            </div>
            {dialogType === 'create' && targetFolder && (
              <p className="text-xs text-muted-foreground">
                Creating subfolder inside: <span className="font-semibold">{targetFolder.name}</span>
              </p>
            )}
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDialogType(null)}>Cancel</Button>
            <Button onClick={handleAction} disabled={isSubmitting || !folderName.trim()}>
              {isSubmitting ? "Processing..." : dialogType === 'create' ? "Create Folder" : "Save Rename"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Delete Confirmation Dialog */}
      <Dialog open={dialogType === 'delete'} onOpenChange={(open) => !open && setDialogType(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Delete Folder</DialogTitle>
            <DialogDescription>
              Are you sure you want to delete this item?
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDialogType(null)}>Cancel</Button>
            <Button variant="destructive" onClick={handleAction} disabled={isSubmitting}>
              {isSubmitting ? "Deleting..." : "Delete Folder"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}

import { FolderOpen } from "lucide-react";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

type FolderPathOption = {
  id: string;
  path: string;
  level: number;
};

type TargetFolderSelectProps = {
  value: string;
  folders: FolderPathOption[];
  onValueChange: (value: string) => void;
};

export function TargetFolderSelect({ value, folders, onValueChange }: TargetFolderSelectProps) {
  return (
    <div className="space-y-2">
      <Label className="flex items-center gap-2 text-xs font-semibold uppercase text-muted-foreground">
        <FolderOpen className="h-3.5 w-3.5" />
        Target Folder (Physical Location)
      </Label>
      <Select value={value} onValueChange={(nextValue) => nextValue !== null && onValueChange(nextValue)}>
        <SelectTrigger className="h-10 text-sm w-full">
          <SelectValue placeholder="Select destination folder...">
            {folders.find((folder) => folder.id === value)?.path}
          </SelectValue>
        </SelectTrigger>
        <SelectContent className="max-h-60">
          {folders.map((folder) => (
            <SelectItem key={folder.id} value={folder.id}>
              <span style={{ paddingLeft: `${folder.level * 12}px` }}>{folder.path}</span>
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
    </div>
  );
}

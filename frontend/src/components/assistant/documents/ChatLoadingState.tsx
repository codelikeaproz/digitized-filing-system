import { Loader2 } from "lucide-react";

export function ChatLoadingState() {
  return (
    <div className="flex items-center gap-3 rounded-lg bg-white px-3.5 py-3 text-sm text-[#55735C] shadow-sm ring-1 ring-[#D7E5D8]">
      <Loader2 className="h-4 w-4 animate-spin text-[#0A4D27]" />
      Searching accessible documents...
    </div>
  );
}

import { FileSearch, Sparkles } from "lucide-react";
import { Button } from "@/components/ui/button";

const INTERNAL_PROMPTS = [
  "Where is the file with code 01-242?",
  "What is this document about?",
  "Find files related to digitization.",
  "Which folder contains the RRL PDF?",
];

interface ChatEmptyStateProps {
  disabled?: boolean;
  onSelectPrompt: (prompt: string) => void;
}

export function ChatEmptyState({ disabled = false, onSelectPrompt }: ChatEmptyStateProps) {
  return (
    <div className="flex min-h-[360px] flex-col items-center justify-center px-5 text-center">
      <div className="mb-4 flex h-12 w-12 items-center justify-center rounded-xl bg-[#E8F1EA] text-[#0A4D27]">
        <FileSearch className="h-6 w-6" />
      </div>
      <h3 className="text-lg font-bold text-[#112217]">How can I help you today?</h3>
      <p className="mt-2 max-w-sm text-sm leading-relaxed text-[#55735C]">
        Ask about file locations, categories, document context, and related records within your access scope.
      </p>
      <div className="mt-5 grid w-full max-w-sm gap-2">
        {INTERNAL_PROMPTS.map((prompt) => (
          <Button
            key={prompt}
            type="button"
            variant="outline"
            disabled={disabled}
            className="h-auto justify-start rounded-lg border-[#D7E5D8] bg-white/85 px-3 py-2 text-left text-xs font-medium text-[#31583B] hover:bg-[#EEF6EF]"
            onClick={() => onSelectPrompt(prompt)}
          >
            <Sparkles className="mr-2 h-3.5 w-3.5 shrink-0 text-[#0A4D27]" />
            {prompt}
          </Button>
        ))}
      </div>
    </div>
  );
}

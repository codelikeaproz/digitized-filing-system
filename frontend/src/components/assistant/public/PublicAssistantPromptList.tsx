import { Button } from "@/components/ui/button";

const PUBLIC_PROMPTS = [
  "What is the Digitized Filing System?",
  "How do I upload a PDF?",
  "How does scanning work?",
  "What are the user roles?",
  "How do I log in?",
];

interface PublicAssistantPromptListProps {
  onSelect: (prompt: string) => void;
}

export function PublicAssistantPromptList({ onSelect }: PublicAssistantPromptListProps) {
  return (
    <div className="space-y-2">
      <p className="text-xs font-semibold uppercase tracking-wide text-[#55735C]">Suggested questions</p>
      <div className="grid gap-2">
        {PUBLIC_PROMPTS.map((prompt) => (
          <Button
            key={prompt}
            type="button"
            variant="outline"
            className="h-auto justify-start rounded-lg border-[#D7E5D8] bg-white/80 px-3 py-2 text-left text-xs font-medium text-[#31583B] hover:bg-[#EEF6EF]"
            onClick={() => onSelect(prompt)}
          >
            {prompt}
          </Button>
        ))}
      </div>
    </div>
  );
}

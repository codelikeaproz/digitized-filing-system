import { Bot, Sparkles } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";

interface DocumentAssistantFloatingButtonProps {
  onClick: () => void;
}

export function DocumentAssistantFloatingButton({ onClick }: DocumentAssistantFloatingButtonProps) {
  return (
    <TooltipProvider>
      <Tooltip>
        <TooltipTrigger>
          <Button
            type="button"
            className="fixed bottom-6 right-6 z-40 h-12 rounded-full bg-[#0A4D27] px-4 text-white shadow-lg shadow-[#0A4D27]/20 hover:bg-[#083E1D]"
            onClick={onClick}
          >
            <Bot className="mr-2 h-4 w-4" />
            Assistant
            <Sparkles className="ml-2 h-3.5 w-3.5" />
          </Button>
        </TooltipTrigger>
        <TooltipContent side="left">Ask Assistant</TooltipContent>
      </Tooltip>
    </TooltipProvider>
  );
}

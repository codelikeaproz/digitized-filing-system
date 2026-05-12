import { MessageCircleQuestion } from "lucide-react";
import { Button } from "@/components/ui/button";

interface PublicAssistantFloatingButtonProps {
  onClick: () => void;
}

export function PublicAssistantFloatingButton({ onClick }: PublicAssistantFloatingButtonProps) {
  return (
    <Button
      type="button"
      className="fixed bottom-6 right-6 z-40 h-12 rounded-full bg-[#0A4D27] px-4 text-white shadow-lg shadow-[#0A4D27]/20 hover:bg-[#083E1D]"
      onClick={onClick}
    >
      <MessageCircleQuestion className="mr-2 h-4 w-4" />
      Ask DFS
    </Button>
  );
}

import { Bot, UserRound } from "lucide-react";
import { cn } from "@/lib/utils";

export type ChatMessageRole = "assistant" | "user";

interface ChatMessageProps {
  role: ChatMessageRole;
  children: React.ReactNode;
}

export function ChatMessage({ role, children }: ChatMessageProps) {
  const isAssistant = role === "assistant";

  return (
    <div className={cn("flex gap-3", isAssistant ? "items-start" : "items-start justify-end")}>
      {isAssistant && (
        <div className="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-[#E8F1EA] text-[#0A4D27]">
          <Bot className="h-4 w-4" />
        </div>
      )}
      <div
        className={cn(
          "max-w-[84%] whitespace-pre-line rounded-lg px-3.5 py-2.5 text-sm leading-relaxed shadow-sm",
          isAssistant
            ? "bg-white text-foreground ring-1 ring-[#D7E5D8]"
            : "bg-[#0A4D27] text-white"
        )}
      >
        {children}
      </div>
      {!isAssistant && (
        <div className="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-[#0A4D27] text-white">
          <UserRound className="h-4 w-4" />
        </div>
      )}
    </div>
  );
}

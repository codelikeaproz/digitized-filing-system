import { useEffect, useRef, useState } from "react";
import { Bot, Minimize2, ShieldCheck } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import { ChatEmptyState } from "./ChatEmptyState";
import { ChatInput } from "./ChatInput";
import { ChatLoadingState } from "./ChatLoadingState";
import { ChatMatchedDocuments } from "./ChatMatchedDocuments";
import { ChatMessage, ChatMessageRole } from "./ChatMessage";
import { AssistantMatchedDocument } from "./ChatDocumentCard";
import { api } from "@/lib/api";
import { getDocumentAssistantOpenRouterSessionId } from "@/lib/assistant/session";

const MONTH_PATTERN =
  /\b(january|jan|february|feb|march|mar|april|apr|may|june|jun|july|jul|august|aug|september|sep|sept|october|oct|november|nov|december|dec)\b/i;
const MONTH_FOLLOW_UP_PATTERN = /^(?:in|on|for|this)?\s*(?:the\s+)?(?:month\s+of\s+)?(january|jan|february|feb|march|mar|april|apr|may|june|jun|july|jul|august|aug|september|sep|sept|october|oct|november|nov|december|dec)\??$/i;

type Message = {
  id: number;
  role: ChatMessageRole;
  content: string;
};

type AssistantMatchResponse = {
  id: number | string;
  title: string;
  code?: string;
  folder_id?: string;
  folder_path?: string;
  category?: string;
  short_description?: string;
  keywords?: string[];
};

type AssistantChatResponse = {
  answer: string;
  matches: AssistantMatchResponse[];
};

interface DocumentAssistantDrawerProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onViewDocument?: (document: AssistantMatchedDocument) => void;
  onOpenFolder?: (document: AssistantMatchedDocument) => void;
}

export function DocumentAssistantDrawer({
  open,
  onOpenChange,
  onViewDocument,
  onOpenFolder,
}: DocumentAssistantDrawerProps) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [matches, setMatches] = useState<AssistantMatchedDocument[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const conversationEndRef = useRef<HTMLDivElement | null>(null);
  const lastResolvedQueryRef = useRef("");

  useEffect(() => {
    conversationEndRef.current?.scrollIntoView({ block: "end" });
  }, [messages, loading, matches]);

  const resolveFollowUpQuery = (query: string) => {
    const followUpMatch = query.match(MONTH_FOLLOW_UP_PATTERN);
    const previousQuery = lastResolvedQueryRef.current;
    if (!followUpMatch || !previousQuery) return query;

    const month = followUpMatch[1];
    if (MONTH_PATTERN.test(previousQuery)) {
      return previousQuery.replace(MONTH_PATTERN, month);
    }

    return `${previousQuery} ${query}`;
  };

  const submitQuery = async (rawQuery = input) => {
    const query = rawQuery.trim();
    if (!query || loading) return;
    const resolvedQuery = resolveFollowUpQuery(query);

    setInput("");
    setLoading(true);
    setMessages((current) => [...current, { id: Date.now(), role: "user", content: query }]);
    setMatches([]);

    try {
      const response = await api.post<AssistantChatResponse>("/api/ai/chat/", {
        query: resolvedQuery,
        session_id: getDocumentAssistantOpenRouterSessionId(),
      });
      lastResolvedQueryRef.current = resolvedQuery;
      setMatches(
        (response.matches || []).map((match) => ({
          id: String(match.id),
          title: match.title,
          code: match.code,
          folderId: match.folder_id ? String(match.folder_id) : undefined,
          folderPath: match.folder_path,
          category: match.category,
          description: match.short_description,
          keywords: match.keywords || [],
        }))
      );
      setMessages((current) => [
        ...current,
        {
          id: Date.now() + 1,
          role: "assistant",
          content: response.answer || "I couldn’t find a matching document in your accessible scope.",
        },
      ]);
    } catch (error) {
      console.error("Document assistant query failed:", error);
      setMessages((current) => [
        ...current,
        {
          id: Date.now() + 1,
          role: "assistant",
          content: "I couldn't reach the assistant service. Please check your internet/server connection and try again.",
        },
      ]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent className="h-dvh max-h-dvh w-[calc(100%-0.5rem)] max-w-[540px] gap-0 overflow-hidden rounded-l-2xl border-l border-[#D7E5D8] bg-[#F7FAF6] p-0 sm:max-w-[520px] lg:max-w-[540px]">
        <SheetHeader className="shrink-0 border-b border-[#D7E5D8] bg-white/90 px-5 py-4 sm:px-6">
          <div className="flex min-w-0 items-start gap-3 pr-20">
            <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-full bg-[#0A4D27] text-white">
              <Bot className="h-5 w-5" />
            </div>
            <div className="min-w-0">
              <SheetTitle className="text-base font-bold text-[#112217]">Document Assistant</SheetTitle>
              <SheetDescription className="mt-1 text-xs leading-relaxed text-[#55735C]">
                Ask about file locations, categories, document context, and related records.
              </SheetDescription>
            </div>
          </div>
          <Button
            type="button"
            variant="ghost"
            size="icon-sm"
            className="absolute right-11 top-3 text-[#55735C]"
            onClick={() => onOpenChange(false)}
          >
            <Minimize2 className="h-4 w-4" />
          </Button>
        </SheetHeader>

        <div className="flex min-h-0 flex-1 flex-col">
          <div className="min-h-0 flex-1 overflow-y-auto overscroll-contain px-5 py-4 sm:px-6">
            <div className="mb-4 rounded-lg bg-[#E8F1EA] px-3 py-2 text-xs leading-relaxed text-[#31583B]">
              <ShieldCheck className="mr-1.5 inline h-3.5 w-3.5" />
              This assistant only answers from documents within your access scope.
            </div>

            {!messages.length && !loading ? (
              <ChatEmptyState onSelectPrompt={submitQuery} />
            ) : (
              <div className="space-y-4">
                {messages.map((message) => (
                  <ChatMessage key={message.id} role={message.role}>
                    {message.content}
                  </ChatMessage>
                ))}
                {loading && <ChatLoadingState />}
                <ChatMatchedDocuments documents={matches} onView={onViewDocument} onOpenFolder={onOpenFolder} />
                <div ref={conversationEndRef} />
              </div>
            )}
          </div>

          <ChatInput value={input} disabled={loading} onChange={setInput} onSubmit={() => submitQuery()} />
        </div>
      </SheetContent>
    </Sheet>
  );
}

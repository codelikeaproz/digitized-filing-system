import { useCallback, useEffect, useRef, useState } from "react";
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
import {
  AssistantPageContext,
  formatAssistantPageContextLabel,
  resolvePageContextQuery,
} from "@/lib/assistant/pageContext";

const MONTH_PATTERN =
  /\b(january|jan|february|feb|march|mar|april|apr|may|june|jun|july|jul|august|aug|september|sep|sept|october|oct|november|nov|december|dec)\b/i;
const MONTH_FOLLOW_UP_PATTERN = /^(?:in|on|for|this)?\s*(?:the\s+)?(?:month\s+of\s+)?(january|jan|february|feb|march|mar|april|apr|may|june|jun|july|jul|august|aug|september|sep|sept|october|oct|november|nov|december|dec)\??$/i;
const DOCUMENT_FOLLOW_UP_PATTERN =
  /^(?:what(?:'s|\s+is)?(?:\s+it|\s+this|\s+that)?\s*about|what\s+is\s+about|tell\s+me\s+(?:more\s+)?about\s+(?:it|this|that)|summarize(?:\s+it|\s+this|\s+the\s+document)?|describe(?:\s+it|\s+this)?|what\s+does\s+it\s+say)\??$/i;
const GREETING_PATTERN =
  /^(hi|hello|hey|good morning|good afternoon|good evening)(?:[!?.…,;:]+)?$/i;
const HELP_PATTERN = /^(help|what can you do|what do you do|how can you help(?: me)?)(?:[!?.…,;:]+)?$/i;

const CHAT_LIST_LIMIT = 5;
const CHAT_COOLDOWN_MS = 800;
const CHAT_DUPLICATE_WINDOW_MS = 30_000;

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
  total_matched?: number | null;
  shown_count?: number | null;
};

type ContextDocument = {
  id: string;
  code?: string;
  title: string;
};

interface DocumentAssistantDrawerProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  pageContext?: AssistantPageContext | null;
  onViewDocument?: (document: AssistantMatchedDocument) => void;
  onOpenFolder?: (document: AssistantMatchedDocument) => void;
}

function normalizeQuery(query: string) {
  return query.trim().toLowerCase();
}

export function DocumentAssistantDrawer({
  open,
  onOpenChange,
  pageContext,
  onViewDocument,
  onOpenFolder,
}: DocumentAssistantDrawerProps) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [matches, setMatches] = useState<AssistantMatchedDocument[]>([]);
  const [matchMeta, setMatchMeta] = useState<{ totalMatched?: number | null; shownCount?: number | null }>({});
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [isCooldown, setIsCooldown] = useState(false);
  const conversationEndRef = useRef<HTMLDivElement | null>(null);
  const lastResolvedQueryRef = useRef("");
  const lastContextDocumentRef = useRef<ContextDocument | null>(null);
  const lastSubmittedQueryRef = useRef("");
  const lastSubmittedAtRef = useRef(0);
  const recentGreetingRef = useRef(false);
  const recentHelpRef = useRef(false);
  const cooldownTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const inputLocked = loading || isCooldown;

  const clearCooldownTimer = useCallback(() => {
    if (cooldownTimeoutRef.current) {
      clearTimeout(cooldownTimeoutRef.current);
      cooldownTimeoutRef.current = null;
    }
  }, []);

  const startCooldown = useCallback(() => {
    clearCooldownTimer();
    setIsCooldown(true);
    cooldownTimeoutRef.current = setTimeout(() => {
      setIsCooldown(false);
      cooldownTimeoutRef.current = null;
    }, CHAT_COOLDOWN_MS);
  }, [clearCooldownTimer]);

  useEffect(() => {
    conversationEndRef.current?.scrollIntoView({ block: "end" });
  }, [messages, loading, matches]);

  useEffect(() => clearCooldownTimer, [clearCooldownTimer]);

  const resolveFollowUpQuery = (query: string) => {
    const trimmed = query.trim();
    const contextDocument = lastContextDocumentRef.current;

    if (contextDocument && DOCUMENT_FOLLOW_UP_PATTERN.test(trimmed)) {
      if (contextDocument.code) {
        return `What is inside code ${contextDocument.code}?`;
      }
      return `What is ${contextDocument.title} about?`;
    }

    const followUpMatch = trimmed.match(MONTH_FOLLOW_UP_PATTERN);
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
    if (!query || inputLocked) return;

    const resolvedQuery = resolvePageContextQuery(resolveFollowUpQuery(query), pageContext);
    const normalized = normalizeQuery(resolvedQuery);
    const now = Date.now();
    const isDuplicate =
      normalized === lastSubmittedQueryRef.current &&
      now - lastSubmittedAtRef.current < CHAT_DUPLICATE_WINDOW_MS;

    const isGreeting = GREETING_PATTERN.test(normalized);
    const isHelp = HELP_PATTERN.test(normalized);

    setInput("");
    setLoading(true);
    setMessages((current) => [...current, { id: now, role: "user", content: query }]);
    setMatches([]);
    setMatchMeta({});

    if (isDuplicate) {
      setMessages((current) => [
        ...current,
        {
          id: now + 1,
          role: "assistant",
          content:
            "You already asked that. Try a document code, folder name, or ask \"how many files do I have?\"",
        },
      ]);
      setLoading(false);
      startCooldown();
      return;
    }

    lastSubmittedQueryRef.current = normalized;
    lastSubmittedAtRef.current = now;

    try {
      const response = await api.post<AssistantChatResponse>(
        "/api/ai/chat/",
        {
          query: resolvedQuery,
          session_id: getDocumentAssistantOpenRouterSessionId(),
          session_hints: {
            recent_greeting: isGreeting && recentGreetingRef.current,
            recent_help: isHelp && recentHelpRef.current,
            folder_id: pageContext?.folderId,
            folder_name: pageContext?.folderName,
            category_id: pageContext?.categoryId,
            category_name: pageContext?.categoryName,
          },
        },
        { skipRateLimitRedirect: true }
      );

      lastResolvedQueryRef.current = resolvedQuery;
      recentGreetingRef.current = isGreeting;
      recentHelpRef.current = isHelp;

      const limitedMatches = (response.matches || []).slice(0, CHAT_LIST_LIMIT);
      setMatches(
        limitedMatches.map((match) => ({
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
      setMatchMeta({
        totalMatched: response.total_matched ?? limitedMatches.length,
        shownCount: response.shown_count ?? limitedMatches.length,
      });
      if (limitedMatches.length > 0) {
        const primary = limitedMatches[0];
        lastContextDocumentRef.current = {
          id: String(primary.id),
          code: primary.code,
          title: primary.title,
        };
      }
      setMessages((current) => [
        ...current,
        {
          id: now + 1,
          role: "assistant",
          content: response.answer || "I couldn’t find a matching document in your accessible scope.",
        },
      ]);
    } catch (error) {
      console.error("Document assistant query failed:", error);
      const isRateLimited =
        typeof error === "object" &&
        error !== null &&
        "status" in error &&
        (error as { status?: number }).status === 429;

      setMessages((current) => [
        ...current,
        {
          id: now + 1,
          role: "assistant",
          content: isRateLimited
            ? "You're sending messages too quickly. Please wait a moment and try again."
            : "I couldn't reach the assistant service. Please check your internet/server connection and try again.",
        },
      ]);
    } finally {
      setLoading(false);
      startCooldown();
    }
  };

  const inputPlaceholder = loading
    ? "Searching accessible documents..."
    : isCooldown
      ? "Please wait a moment..."
      : undefined;

  const pageContextLabel = formatAssistantPageContextLabel(pageContext);

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
            {pageContextLabel ? (
              <div className="mb-4 rounded-lg border border-[#C9DECB] bg-white px-3 py-2 text-xs leading-relaxed text-[#31583B]">
                Using current view: {pageContextLabel}
              </div>
            ) : null}

            {!messages.length && !loading ? (
              <ChatEmptyState disabled={inputLocked} onSelectPrompt={submitQuery} />
            ) : (
              <div className="space-y-4">
                {messages.map((message) => (
                  <ChatMessage key={message.id} role={message.role}>
                    {message.content}
                  </ChatMessage>
                ))}
                {loading && <ChatLoadingState />}
                <ChatMatchedDocuments
                  documents={matches}
                  totalMatched={matchMeta.totalMatched}
                  shownCount={matchMeta.shownCount}
                  onView={onViewDocument}
                  onOpenFolder={onOpenFolder}
                />
                <div ref={conversationEndRef} />
              </div>
            )}
          </div>

          <ChatInput
            value={input}
            disabled={inputLocked}
            placeholder={inputPlaceholder}
            onChange={setInput}
            onSubmit={() => submitQuery()}
          />
        </div>
      </SheetContent>
    </Sheet>
  );
}

import { type FormEvent, useEffect, useRef, useState } from "react";
import { Bot, Loader2, Send, Sparkles, X } from "lucide-react";

import { postAiChat, type AiChatMessage } from "@/api/ai";
import { Button } from "@/components/ui/button";
import { useTranslation } from "@/contexts/LanguageContext";
import type { SalesAlert } from "@/types/alerts";

type AIInsightPanelProps = {
  alert: SalesAlert | null;
  onClose: () => void;
};

type ChatMessage = {
  id: string;
  role: "user" | "assistant";
  content: string;
};

export function AIInsightPanel({ alert, onClose }: AIInsightPanelProps) {
  const { t } = useTranslation();
  const [question, setQuestion] = useState("");
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!alert) return;
    setQuestion("");
    setMessages([]);
  }, [alert]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isLoading]);

  if (!alert) return null;

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const trimmedQuestion = question.trim();
    if (!trimmedQuestion || isLoading) return;

    const userMessage: ChatMessage = {
      id: `user-${Date.now()}`,
      role: "user",
      content: trimmedQuestion,
    };

    setMessages((prev) => [...prev, userMessage]);
    setQuestion("");
    setIsLoading(true);

    const history: AiChatMessage[] = messages.map((m) => ({
      role: m.role,
      content: m.content,
    }));

    try {
      const responseText = await postAiChat(alert!, history, trimmedQuestion);
      const assistantMessage: ChatMessage = {
        id: `assistant-${Date.now()}`,
        role: "assistant",
        content: responseText,
      };
      setMessages((prev) => [...prev, assistantMessage]);
    } catch {
      const errorMessage: ChatMessage = {
        id: `error-${Date.now()}`,
        role: "assistant",
        content: t("ai.error"),
      };
      setMessages((prev) => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex justify-end bg-slate-950/30">
      <aside
        aria-label={t("ai.title")}
        className="flex h-full w-full max-w-xl flex-col border-l bg-card shadow-2xl"
      >
        <header className="flex items-start justify-between gap-4 border-b px-5 py-4">
          <div>
            <div className="flex items-center gap-2 text-sm font-medium text-primary">
              <Sparkles className="size-4" aria-hidden="true" />
              {t("ai.title")}
            </div>
            <h2 className="mt-1 text-lg font-semibold text-foreground">{alert.clientName}</h2>
            <p className="mt-1 text-sm text-muted-foreground">
              {t("ai.description")}
            </p>
          </div>
          <Button aria-label={t("modal.close")} size="icon" type="button" variant="ghost" onClick={onClose}>
            <X className="size-4" aria-hidden="true" />
          </Button>
        </header>

        <div className="flex-1 space-y-3 overflow-y-auto bg-slate-50 px-5 py-5">
          {messages.length === 0 && !isLoading && (
            <p className="text-center text-sm text-muted-foreground pt-8">
              {t("ai.placeholder")}
            </p>
          )}
          {messages.map((message) => (
            <div
              key={message.id}
              className={
                message.role === "assistant"
                  ? "mr-8 rounded-lg border bg-white px-4 py-3 text-sm leading-6 text-foreground shadow-sm"
                  : "ml-8 rounded-lg bg-primary px-4 py-3 text-sm leading-6 text-primary-foreground"
              }
            >
              {message.role === "assistant" ? (
                <div className="mb-2 flex items-center gap-2 text-xs font-medium uppercase tracking-wide text-muted-foreground">
                  <Bot className="size-3.5" aria-hidden="true" />
                  {t("ai.mock_ai")}
                </div>
              ) : null}
              {message.role === "assistant" ? (
                <div className="space-y-2">
                  {message.content
                    .split(/\n\n+/)
                    .map((para) => para.trim())
                    .filter(Boolean)
                    .map((para, i) => (
                      <p key={i}>{para}</p>
                    ))}
                </div>
              ) : (
                message.content
              )}
            </div>
          ))}
          {isLoading && (
            <div className="mr-8 rounded-lg border bg-white px-4 py-3 text-sm leading-6 text-muted-foreground shadow-sm">
              <div className="mb-2 flex items-center gap-2 text-xs font-medium uppercase tracking-wide text-muted-foreground">
                <Bot className="size-3.5" aria-hidden="true" />
                {t("ai.mock_ai")}
              </div>
              <Loader2 className="size-4 animate-spin" aria-label="Carregant..." />
            </div>
          )}
          <div ref={bottomRef} />
        </div>

        <form className="border-t bg-card p-4" onSubmit={handleSubmit}>
          <label className="sr-only" htmlFor="ai-question">
            {t("ai.title")}
          </label>
          <div className="flex gap-2">
            <input
              className="h-10 min-w-0 flex-1 rounded-md border bg-background px-3 text-sm outline-none transition-colors placeholder:text-muted-foreground focus:border-ring focus:ring-2 focus:ring-ring/20 disabled:opacity-50"
              disabled={isLoading}
              id="ai-question"
              placeholder={t("ai.placeholder")}
              value={question}
              onChange={(event) => setQuestion(event.target.value)}
            />
            <Button disabled={isLoading || !question.trim()} type="submit">
              {isLoading ? (
                <Loader2 className="size-4 animate-spin" aria-hidden="true" />
              ) : (
                <Send className="size-4" aria-hidden="true" />
              )}
              {t("ai.send")}
            </Button>
          </div>
        </form>
      </aside>
    </div>
  );
}

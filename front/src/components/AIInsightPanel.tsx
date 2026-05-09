import { type FormEvent, useEffect, useMemo, useState } from "react";
import { Bot, Send, Sparkles, X } from "lucide-react";

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

  const openingMessage = useMemo(() => {
    if (!alert) {
      return "";
    }

    return t("ai.opening", {
      name: alert.clientName,
      churn: alert.churnProbability,
      buy: alert.purchasePropensity,
    });
  }, [alert, t]);

  useEffect(() => {
    if (!alert) {
      return;
    }

    setQuestion("");
    setMessages([
      {
        id: `${alert.id}-opening`,
        role: "assistant",
        content: openingMessage,
      },
    ]);
  }, [alert, openingMessage]);

  if (!alert) {
    return null;
  }

  const activeAlert = alert;

  function createMockResponse(alert: SalesAlert, question: string) {
    const normalizedQuestion = question.toLowerCase();

    if (normalizedQuestion.includes("action") || normalizedQuestion.includes("acción") || normalizedQuestion.includes("acció")) {
      return t("ai.action_rec", { name: alert.clientName });
    }

    if (normalizedQuestion.includes("why") || normalizedQuestion.includes("por qué") || normalizedQuestion.includes("per què")) {
      return t("ai.why_rec", { explanation: alert.explanation });
    }

    return t("ai.default_rec", {
      name: alert.clientName,
      churn: alert.churnProbability,
      buy: alert.purchasePropensity,
    });
  }

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const trimmedQuestion = question.trim();

    if (!trimmedQuestion) {
      return;
    }

    const userMessage: ChatMessage = {
      id: `user-${Date.now()}`,
      role: "user",
      content: trimmedQuestion,
    };
    const assistantMessage: ChatMessage = {
      id: `assistant-${Date.now()}`,
      role: "assistant",
      content: createMockResponse(activeAlert, trimmedQuestion),
    };

    setMessages((currentMessages) => [...currentMessages, userMessage, assistantMessage]);
    setQuestion("");
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
            <h2 className="mt-1 text-lg font-semibold text-foreground">{activeAlert.clientName}</h2>
            <p className="mt-1 text-sm text-muted-foreground">
              {t("ai.description")}
            </p>
          </div>
          <Button aria-label={t("modal.close")} size="icon" type="button" variant="ghost" onClick={onClose}>
            <X className="size-4" aria-hidden="true" />
          </Button>
        </header>

        <div className="flex-1 space-y-3 overflow-y-auto bg-slate-50 px-5 py-5">
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
              {message.content}
            </div>
          ))}
        </div>

        <form className="border-t bg-card p-4" onSubmit={handleSubmit}>
          <label className="sr-only" htmlFor="ai-question">
            {t("ai.title")}
          </label>
          <div className="flex gap-2">
            <input
              className="h-10 min-w-0 flex-1 rounded-md border bg-background px-3 text-sm outline-none transition-colors placeholder:text-muted-foreground focus:border-ring focus:ring-2 focus:ring-ring/20"
              id="ai-question"
              placeholder={t("ai.placeholder")}
              value={question}
              onChange={(event) => setQuestion(event.target.value)}
            />
            <Button type="submit">
              <Send className="size-4" aria-hidden="true" />
              {t("ai.send")}
            </Button>
          </div>
        </form>
      </aside>
    </div>
  );
}

import { apiRequest } from "@/api/client";
import type { SalesAlert } from "@/types/alerts";

type ChatRole = "user" | "assistant";

export type AiChatMessage = {
  role: ChatRole;
  content: string;
};

type AlertContext = Pick<
  SalesAlert,
  | "clientName"
  | "riskLevel"
  | "churnProbability"
  | "purchasePropensity"
  | "customerValue"
  | "churnType"
  | "explanation"
>;

type ChatRequest = {
  alert: AlertContext;
  history: AiChatMessage[];
  question: string;
};

type ChatResponse = {
  response: string;
};

export async function postAiChat(
  alert: AlertContext,
  history: AiChatMessage[],
  question: string,
): Promise<string> {
  const body: ChatRequest = { alert, history, question };
  const result = await apiRequest<ChatResponse>("/ai/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  return result.response;
}

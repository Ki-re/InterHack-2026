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
  | "alertContextJson"
  | "predictedNextPurchase"
  | "lastOrderDate"
>;

type ChatRequest = {
  alert: AlertContext;
  history: AiChatMessage[];
  question: string;
};

type ChatResponse = {
  response: string;
};

export async function postTranscribe(audioBlob: Blob): Promise<string> {
  const form = new FormData();
  form.append("file", audioBlob, "audio.webm");
  const result = await apiRequest<{ text: string }>("/audio/transcribe", {
    method: "POST",
    body: form,
  });
  return result.text;
}

export async function postSynthesize(text: string): Promise<Blob> {
  const VITE_API_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8000";
  const res = await fetch(`${VITE_API_URL}/audio/synthesize`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text }),
  });
  if (!res.ok) throw new Error("TTS failed");
  return res.blob();
}

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

import { type FormEvent, useEffect, useRef, useState } from "react";
import { Bot, Loader2, Mic, MicOff, Send, Sparkles, Volume2, VolumeX, X } from "lucide-react";

import { postAiChat, postSynthesize, postTranscribe, type AiChatMessage } from "@/api/ai";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
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
  const [isMuted, setIsMuted] = useState(false);
  const [isRecording, setIsRecording] = useState(false);
  const [hasRecording, setHasRecording] = useState(false);
  const [waveformBars, setWaveformBars] = useState<number[]>(Array(24).fill(0));

  const bottomRef = useRef<HTMLDivElement>(null);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const audioCtxRef = useRef<AudioContext | null>(null);
  const animFrameRef = useRef<number | null>(null);
  // Ref so playTTS always reads latest mute state even after async delays
  const isMutedRef = useRef(isMuted);

  useEffect(() => {
    isMutedRef.current = isMuted;
  }, [isMuted]);

  useEffect(() => {
    if (!alert) return;
    setQuestion("");
    setMessages([]);
    setHasRecording(false);
    chunksRef.current = [];
  }, [alert]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isLoading]);

  useEffect(() => {
    return () => {
      if (animFrameRef.current) cancelAnimationFrame(animFrameRef.current);
      audioCtxRef.current?.close();
    };
  }, []);

  if (!alert) return null;

  async function playTTS(text: string) {
    if (isMutedRef.current) return;
    try {
      const blob = await postSynthesize(text);
      const url = URL.createObjectURL(blob);
      const audio = new Audio(url);
      audio.onended = () => URL.revokeObjectURL(url);
      await audio.play();
    } catch {
      // TTS failure is non-critical
    }
  }

  async function sendMessage(text: string) {
    const userMessage: ChatMessage = {
      id: `user-${Date.now()}`,
      role: "user",
      content: text,
    };
    setMessages((prev) => [...prev, userMessage]);
    setIsLoading(true);

    const history: AiChatMessage[] = messages.map((m) => ({
      role: m.role,
      content: m.content,
    }));

    try {
      const responseText = await postAiChat(alert!, history, text);
      const assistantMessage: ChatMessage = {
        id: `assistant-${Date.now()}`,
        role: "assistant",
        content: responseText,
      };
      setMessages((prev) => [...prev, assistantMessage]);
      await playTTS(responseText);
    } catch {
      setMessages((prev) => [
        ...prev,
        { id: `error-${Date.now()}`, role: "assistant", content: t("ai.error") },
      ]);
    } finally {
      setIsLoading(false);
    }
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (isLoading || isRecording) return;

    if (hasRecording && chunksRef.current.length > 0) {
      setHasRecording(false);
      setIsLoading(true);
      const blob = new Blob(chunksRef.current, { type: "audio/webm" });
      chunksRef.current = [];
      try {
        const text = await postTranscribe(blob);
        const trimmed = text.trim();
        if (!trimmed) return;
        setIsLoading(false);
        await sendMessage(trimmed);
      } catch {
        setMessages((prev) => [
          ...prev,
          { id: `error-${Date.now()}`, role: "assistant", content: t("ai.error") },
        ]);
        setIsLoading(false);
      }
      return;
    }

    const trimmed = question.trim();
    if (!trimmed) return;
    setQuestion("");
    await sendMessage(trimmed);
  }

  async function startRecording() {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const recorder = new MediaRecorder(stream, { mimeType: "audio/webm" });
      chunksRef.current = [];

      const audioCtx = new AudioContext();
      audioCtxRef.current = audioCtx;
      const source = audioCtx.createMediaStreamSource(stream);
      const analyser = audioCtx.createAnalyser();
      analyser.fftSize = 64;
      source.connect(analyser);

      function draw() {
        const data = new Uint8Array(analyser.frequencyBinCount);
        analyser.getByteFrequencyData(data);
        setWaveformBars(Array.from(data.slice(1, 25)));
        animFrameRef.current = requestAnimationFrame(draw);
      }
      draw();

      recorder.ondataavailable = (e) => {
        if (e.data.size > 0) chunksRef.current.push(e.data);
      };

      recorder.onstop = () => {
        stream.getTracks().forEach((t) => t.stop());
        if (animFrameRef.current) {
          cancelAnimationFrame(animFrameRef.current);
          animFrameRef.current = null;
        }
        audioCtx.close();
        setWaveformBars(Array(24).fill(0));
        setHasRecording(true);
      };

      recorder.start();
      mediaRecorderRef.current = recorder;
      setIsRecording(true);
    } catch {
      // mic permission denied
    }
  }

  function stopRecording() {
    mediaRecorderRef.current?.stop();
    mediaRecorderRef.current = null;
    setIsRecording(false);
  }

  function cancelRecording() {
    chunksRef.current = [];
    setHasRecording(false);
  }

  function handleMicClick() {
    if (isRecording) {
      stopRecording();
    } else if (hasRecording) {
      cancelRecording();
    } else {
      startRecording();
    }
  }

  const canSend = !isLoading && !isRecording && (hasRecording || !!question.trim());

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
            <p className="mt-1 text-sm text-muted-foreground">{t("ai.description")}</p>
          </div>
          <div className="flex items-center gap-1">
            <Button
              aria-label={isMuted ? "Activar audio" : "Silenciar audio"}
              size="icon"
              type="button"
              variant={isMuted ? "secondary" : "ghost"}
              onClick={() => setIsMuted((m) => !m)}
            >
              {isMuted ? (
                <VolumeX className="size-4" aria-hidden="true" />
              ) : (
                <Volume2 className="size-4" aria-hidden="true" />
              )}
            </Button>
            <Button aria-label={t("modal.close")} size="icon" type="button" variant="ghost" onClick={onClose}>
              <X className="size-4" aria-hidden="true" />
            </Button>
          </div>
        </header>

        <div className="flex-1 space-y-3 overflow-y-auto bg-slate-50 px-5 py-5">
          {messages.length === 0 && !isLoading && (
            <p className="text-center text-sm text-muted-foreground pt-8">{t("ai.placeholder")}</p>
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
            <Button
              aria-label={
                isRecording ? "Parar grabación" : hasRecording ? "Cancelar audio" : "Grabar audio"
              }
              disabled={isLoading}
              size="icon"
              type="button"
              variant={isRecording ? "destructive" : "outline"}
              onClick={handleMicClick}
            >
              {isRecording ? (
                <MicOff className="size-4" aria-hidden="true" />
              ) : (
                <Mic
                  className={cn("size-4", hasRecording && "text-primary")}
                  aria-hidden="true"
                />
              )}
            </Button>

            {isRecording ? (
              <div className="flex h-10 min-w-0 flex-1 items-end gap-px rounded-md border bg-background px-3 pb-1.5">
                {waveformBars.map((bar, i) => (
                  <div
                    key={i}
                    className="w-1.5 flex-1 rounded-full bg-primary transition-all duration-75"
                    style={{ height: `${Math.max(3, (bar / 255) * 28)}px` }}
                  />
                ))}
              </div>
            ) : (
              <input
                className="h-10 min-w-0 flex-1 rounded-md border bg-background px-3 text-sm outline-none transition-colors placeholder:text-muted-foreground focus:border-ring focus:ring-2 focus:ring-ring/20 disabled:opacity-50"
                disabled={isLoading || hasRecording}
                id="ai-question"
                placeholder={hasRecording ? "Audio listo — pulsa enviar" : t("ai.placeholder")}
                value={question}
                onChange={(event) => setQuestion(event.target.value)}
              />
            )}

            <Button
              disabled={!canSend}
              type="submit"
              className={cn(hasRecording && "bg-blue-600 hover:bg-blue-700 text-white")}
            >
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

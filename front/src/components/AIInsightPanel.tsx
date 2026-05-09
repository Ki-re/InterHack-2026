import { type FormEvent, useEffect, useRef, useState } from "react";
import { Bot, Loader2, Mic, Pause, Play, Send, Sparkles, Square, Trash2, Volume2, VolumeX, X } from "lucide-react";

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

type RecordingMode = "idle" | "recording" | "preview";

const BARS = 40;
const SAMPLE_MS = 50;

function formatDuration(s: number) {
  return `${Math.floor(s / 60).toString().padStart(2, "0")}:${(s % 60).toString().padStart(2, "0")}`;
}

function getRms(analyser: AnalyserNode): number {
  const data = new Uint8Array(analyser.fftSize);
  analyser.getByteTimeDomainData(data);
  let sum = 0;
  for (const v of data) {
    const n = (v - 128) / 128;
    sum += n * n;
  }
  return Math.sqrt(sum / data.length);
}

export function AIInsightPanel({ alert, onClose }: AIInsightPanelProps) {
  const { t } = useTranslation();
  const [question, setQuestion] = useState("");
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isMuted, setIsMuted] = useState(false);
  const [mode, setMode] = useState<RecordingMode>("idle");
  const [recordingSeconds, setRecordingSeconds] = useState(0);
  const [liveBars, setLiveBars] = useState<number[]>(Array(BARS).fill(0));
  const [capturedBars, setCapturedBars] = useState<number[]>(Array(BARS).fill(0));
  const [isPlayingPreview, setIsPlayingPreview] = useState(false);
  const [playheadProgress, setPlayheadProgress] = useState(0);

  const bottomRef = useRef<HTMLDivElement>(null);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const mimeTypeRef = useRef("audio/webm");
  const audioCtxRef = useRef<AudioContext | null>(null);
  const analyserRef = useRef<AnalyserNode | null>(null);
  const rollingRef = useRef<number[]>(Array(BARS).fill(0));
  const sampleTimerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const durationTimerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const previewAudioRef = useRef<HTMLAudioElement | null>(null);
  const isMutedRef = useRef(isMuted);

  useEffect(() => { isMutedRef.current = isMuted; }, [isMuted]);

  useEffect(() => {
    if (!alert) return;
    setQuestion("");
    setMessages([]);
    resetRecording();
  }, [alert]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isLoading]);

  useEffect(() => () => cleanup(), []);

  if (!alert) return null;

  function cleanup() {
    if (sampleTimerRef.current) clearInterval(sampleTimerRef.current);
    if (durationTimerRef.current) clearInterval(durationTimerRef.current);
    audioCtxRef.current?.close();
    previewAudioRef.current?.pause();
  }

  function resetRecording() {
    cleanup();
    mediaRecorderRef.current?.stop();
    mediaRecorderRef.current = null;
    chunksRef.current = [];
    rollingRef.current = Array(BARS).fill(0);
    audioCtxRef.current = null;
    analyserRef.current = null;
    previewAudioRef.current = null;
    setMode("idle");
    setRecordingSeconds(0);
    setLiveBars(Array(BARS).fill(0));
    setCapturedBars(Array(BARS).fill(0));
    setIsPlayingPreview(false);
    setPlayheadProgress(0);
  }

  async function startRecording() {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mimeType = MediaRecorder.isTypeSupported("audio/webm") ? "audio/webm" : "audio/mp4";
      mimeTypeRef.current = mimeType;
      const recorder = new MediaRecorder(stream, { mimeType });
      chunksRef.current = [];

      const audioCtx = new AudioContext();
      audioCtxRef.current = audioCtx;
      const source = audioCtx.createMediaStreamSource(stream);
      const analyser = audioCtx.createAnalyser();
      analyser.fftSize = 256;
      source.connect(analyser);
      analyserRef.current = analyser;

      let secs = 0;
      durationTimerRef.current = setInterval(() => { secs++; setRecordingSeconds(secs); }, 1000);

      sampleTimerRef.current = setInterval(() => {
        const amp = Math.min(1, getRms(analyser) * 18);
        rollingRef.current = [...rollingRef.current.slice(1), amp];
        setLiveBars([...rollingRef.current]);
      }, SAMPLE_MS);

      recorder.ondataavailable = (e) => { if (e.data.size > 0) chunksRef.current.push(e.data); };

      recorder.onstop = () => {
        stream.getTracks().forEach((t) => t.stop());
        if (sampleTimerRef.current) clearInterval(sampleTimerRef.current);
        if (durationTimerRef.current) clearInterval(durationTimerRef.current);
        audioCtx.close();

        const captured = [...rollingRef.current];
        setCapturedBars(captured);

        const blob = new Blob(chunksRef.current, { type: mimeType });
        const url = URL.createObjectURL(blob);
        const audio = new Audio(url);
        audio.onended = () => { setIsPlayingPreview(false); setPlayheadProgress(0); };
        audio.ontimeupdate = () => {
          if (audio.duration) setPlayheadProgress(audio.currentTime / audio.duration);
        };
        previewAudioRef.current = audio;
        setMode("preview");
      };

      recorder.start();
      mediaRecorderRef.current = recorder;
      setMode("recording");
    } catch {
      // mic denied
    }
  }

  function stopRecording() {
    mediaRecorderRef.current?.stop();
    mediaRecorderRef.current = null;
  }

  function togglePreview() {
    const audio = previewAudioRef.current;
    if (!audio) return;
    if (isPlayingPreview) {
      audio.pause();
      setIsPlayingPreview(false);
    } else {
      void audio.play();
      setIsPlayingPreview(true);
    }
  }

  async function playTTS(text: string) {
    if (isMutedRef.current) return;
    try {
      const blob = await postSynthesize(text);
      const url = URL.createObjectURL(blob);
      const audio = new Audio(url);
      audio.onended = () => URL.revokeObjectURL(url);
      await audio.play();
    } catch {
      // non-critical
    }
  }

  async function sendMessage(text: string) {
    const userMsg: ChatMessage = { id: `user-${Date.now()}`, role: "user", content: text };
    setMessages((prev) => [...prev, userMsg]);
    setIsLoading(true);

    const history: AiChatMessage[] = messages.map((m) => ({ role: m.role, content: m.content }));

    try {
      const responseText = await postAiChat(alert!, history, text);
      setMessages((prev) => [
        ...prev,
        { id: `assistant-${Date.now()}`, role: "assistant", content: responseText },
      ]);
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
    if (isLoading) return;

    if (mode === "preview" && chunksRef.current.length > 0) {
      previewAudioRef.current?.pause();
      const blob = new Blob(chunksRef.current, { type: mimeTypeRef.current });
      resetRecording();
      setIsLoading(true);
      try {
        const text = await postTranscribe(blob);
        const trimmed = text.trim();
        setIsLoading(false);
        if (trimmed) await sendMessage(trimmed);
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

  const barHeightPx = (v: number) => Math.max(4, Math.min(28, v * 28));

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
              {isMuted ? <VolumeX className="size-4" /> : <Volume2 className="size-4" />}
            </Button>
            <Button aria-label={t("modal.close")} size="icon" type="button" variant="ghost" onClick={onClose}>
              <X className="size-4" />
            </Button>
          </div>
        </header>

        <div className="flex-1 space-y-3 overflow-y-auto bg-slate-50 px-5 py-5">
          {messages.length === 0 && !isLoading && (
            <p className="text-center text-sm text-muted-foreground pt-8">{t("ai.placeholder")}</p>
          )}
          {messages.map((msg) => (
            <div
              key={msg.id}
              className={
                msg.role === "assistant"
                  ? "mr-8 rounded-lg border bg-white px-4 py-3 text-sm leading-6 text-foreground shadow-sm"
                  : "ml-8 rounded-lg bg-primary px-4 py-3 text-sm leading-6 text-primary-foreground"
              }
            >
              {msg.role === "assistant" && (
                <div className="mb-2 flex items-center gap-2 text-xs font-medium uppercase tracking-wide text-muted-foreground">
                  <Bot className="size-3.5" />
                  {t("ai.mock_ai")}
                </div>
              )}
              {msg.role === "assistant" ? (
                <div className="space-y-2">
                  {msg.content.split(/\n\n+/).map((p) => p.trim()).filter(Boolean).map((p, i) => (
                    <p key={i}>{p}</p>
                  ))}
                </div>
              ) : msg.content}
            </div>
          ))}
          {isLoading && (
            <div className="mr-8 rounded-lg border bg-white px-4 py-3 text-sm leading-6 text-muted-foreground shadow-sm">
              <div className="mb-2 flex items-center gap-2 text-xs font-medium uppercase tracking-wide text-muted-foreground">
                <Bot className="size-3.5" />
                {t("ai.mock_ai")}
              </div>
              <Loader2 className="size-4 animate-spin" />
            </div>
          )}
          <div ref={bottomRef} />
        </div>

        <form className="border-t bg-card p-4" onSubmit={handleSubmit}>
          <label className="sr-only" htmlFor="ai-question">{t("ai.title")}</label>

          {/* ── IDLE ─────────────────────────────── */}
          {mode === "idle" && (
            <div className="flex gap-2">
              <Button
                aria-label="Grabar audio"
                disabled={isLoading}
                size="icon"
                type="button"
                variant="outline"
                onClick={startRecording}
              >
                <Mic className="size-4" />
              </Button>
              <input
                className="h-10 min-w-0 flex-1 rounded-md border bg-background px-3 text-sm outline-none transition-colors placeholder:text-muted-foreground focus:border-ring focus:ring-2 focus:ring-ring/20 disabled:opacity-50"
                disabled={isLoading}
                id="ai-question"
                placeholder={t("ai.placeholder")}
                value={question}
                onChange={(e) => setQuestion(e.target.value)}
              />
              <Button disabled={isLoading || !question.trim()} type="submit">
                {isLoading ? <Loader2 className="size-4 animate-spin" /> : <Send className="size-4" />}
                {t("ai.send")}
              </Button>
            </div>
          )}

          {/* ── RECORDING ────────────────────────── */}
          {mode === "recording" && (
            <div className="flex items-center gap-2">
              <Button
                aria-label="Cancelar"
                size="icon"
                type="button"
                variant="ghost"
                className="shrink-0 text-muted-foreground hover:text-destructive"
                onClick={resetRecording}
              >
                <Trash2 className="size-4" />
              </Button>

              <div className="flex flex-1 items-center gap-1.5 rounded-full border bg-background px-3 py-1.5 h-10 overflow-hidden">
                <span className="size-2 shrink-0 rounded-full bg-destructive animate-pulse" />
                <div className="flex flex-1 items-center justify-between gap-px h-full">
                  {liveBars.map((v, i) => (
                    <div
                      key={i}
                      className="w-1 shrink-0 rounded-full bg-destructive"
                      style={{ height: `${barHeightPx(v)}px` }}
                    />
                  ))}
                </div>
                <span className="text-xs text-muted-foreground shrink-0 tabular-nums ml-1">
                  {formatDuration(recordingSeconds)}
                </span>
              </div>

              <Button
                aria-label="Parar grabación"
                size="icon"
                type="button"
                variant="destructive"
                className="shrink-0 rounded-full"
                onClick={stopRecording}
              >
                <Square className="size-3 fill-current" />
              </Button>
            </div>
          )}

          {/* ── PREVIEW ──────────────────────────── */}
          {mode === "preview" && (
            <div className="flex items-center gap-2">
              <Button
                aria-label="Descartar audio"
                size="icon"
                type="button"
                variant="ghost"
                className="shrink-0 text-muted-foreground hover:text-destructive"
                onClick={resetRecording}
              >
                <Trash2 className="size-4" />
              </Button>

              <Button
                aria-label={isPlayingPreview ? "Pausar" : "Reproducir"}
                size="icon"
                type="button"
                variant="outline"
                className="shrink-0 rounded-full"
                onClick={togglePreview}
              >
                {isPlayingPreview ? <Pause className="size-4" /> : <Play className="size-4" />}
              </Button>

              <div className="flex flex-1 items-center gap-px rounded-full border bg-background px-3 py-1.5 h-10 overflow-hidden">
                {capturedBars.map((v, i) => (
                  <div
                    key={i}
                    className={cn(
                      "w-1 shrink-0 rounded-full transition-colors",
                      i / BARS < playheadProgress ? "bg-primary" : "bg-muted-foreground/25",
                    )}
                    style={{ height: `${barHeightPx(v)}px` }}
                  />
                ))}
                <span className="text-xs text-muted-foreground shrink-0 tabular-nums ml-2">
                  {formatDuration(recordingSeconds)}
                </span>
              </div>

              <Button
                disabled={isLoading}
                type="submit"
                size="icon"
                className="shrink-0 rounded-full bg-blue-600 hover:bg-blue-700 text-white"
                aria-label="Enviar audio"
              >
                {isLoading ? <Loader2 className="size-4 animate-spin" /> : <Send className="size-4" />}
              </Button>
            </div>
          )}
        </form>
      </aside>
    </div>
  );
}

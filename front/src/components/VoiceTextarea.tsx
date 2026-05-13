import { useRef, useState } from "react";
import { Loader2, Mic, Square } from "lucide-react";

import { postTranscribe } from "@/api/ai";
import { Button } from "@/components/ui/button";
import { useDemoMode } from "@/contexts/DemoModeContext";
import { useTranslation } from "@/contexts/LanguageContext";
import { cn } from "@/lib/utils";

type VoiceTextareaProps = {
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
  className?: string;
  disabled?: boolean;
};

const BARS = 32;

export function VoiceTextarea({ value, onChange, placeholder, className, disabled }: VoiceTextareaProps) {
  const { t } = useTranslation();
  const { isDemoMode, showDemoNotice } = useDemoMode();
  const [isRecording, setIsRecording] = useState(false);
  const [isTranscribing, setIsTranscribing] = useState(false);
  const [waveformBars, setWaveformBars] = useState<number[]>(Array(BARS).fill(0));

  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const audioCtxRef = useRef<AudioContext | null>(null);
  const sampleTimerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const analyserRef = useRef<AnalyserNode | null>(null);

  function getRms(): number {
    if (!analyserRef.current) return 0;
    const data = new Uint8Array(analyserRef.current.fftSize);
    analyserRef.current.getByteTimeDomainData(data);
    let sum = 0;
    for (const v of data) {
      const n = (v - 128) / 128;
      sum += n * n;
    }
    return Math.sqrt(sum / data.length);
  }

  async function startRecording() {
    if (isDemoMode) {
      showDemoNotice(t("demo.stt_disabled"));
      return;
    }

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mimeType = MediaRecorder.isTypeSupported("audio/webm") ? "audio/webm" : "audio/mp4";
      const recorder = new MediaRecorder(stream, { mimeType });
      chunksRef.current = [];

      const audioCtx = new AudioContext();
      audioCtxRef.current = audioCtx;
      const source = audioCtx.createMediaStreamSource(stream);
      const analyser = audioCtx.createAnalyser();
      analyser.fftSize = 256;
      source.connect(analyser);
      analyserRef.current = analyser;

      sampleTimerRef.current = setInterval(() => {
        const amp = Math.min(1, getRms() * 18);
        setWaveformBars((prev) => [...prev.slice(1), amp]);
      }, 50);

      recorder.ondataavailable = (e) => { if (e.data.size > 0) chunksRef.current.push(e.data); };

      recorder.onstop = async () => {
        stream.getTracks().forEach((t) => t.stop());
        if (sampleTimerRef.current) clearInterval(sampleTimerRef.current);
        audioCtx.close();
        setWaveformBars(Array(BARS).fill(0));
        setIsRecording(false);

        const blob = new Blob(chunksRef.current, { type: mimeType });
        chunksRef.current = [];
        setIsTranscribing(true);
        try {
          const text = await postTranscribe(blob);
          const trimmed = text.trim();
          if (trimmed) onChange(value ? `${value} ${trimmed}` : trimmed);
        } catch {
          // non-critical
        } finally {
          setIsTranscribing(false);
        }
      };

      recorder.start();
      mediaRecorderRef.current = recorder;
      setIsRecording(true);
    } catch {
      // mic denied
    }
  }

  function stopRecording() {
    mediaRecorderRef.current?.stop();
    mediaRecorderRef.current = null;
  }

  const busy = disabled || isTranscribing;

  if (isRecording) {
    return (
      <div className="w-full rounded-md border-2 border-destructive bg-destructive/5 px-4 py-3 flex flex-col gap-2">
        {/* REC badge */}
        <div className="flex items-center gap-1.5 shrink-0">
          <span className="size-2 rounded-full bg-destructive animate-pulse" />
          <span className="text-xs font-medium text-destructive">REC</span>
        </div>

        {/* Waveform — fixed height, bars can't push layout */}
        <div className="flex h-8 shrink-0 items-center justify-between gap-px overflow-hidden">
          {waveformBars.map((v, i) => (
            <div
              key={i}
              className="flex-1 rounded-full bg-destructive"
              style={{ height: `${Math.max(3, Math.min(28, v * 28))}px` }}
            />
          ))}
        </div>

        {/* Stop button — always visible, never displaced */}
        <button
          aria-label={t("audio.stop")}
          type="button"
          className="flex w-full shrink-0 items-center justify-center gap-2 rounded-full bg-destructive py-1.5 text-sm font-medium text-destructive-foreground shadow-md transition-transform active:scale-95 hover:bg-destructive/90"
          onClick={stopRecording}
        >
          <Square className="size-3.5 fill-current" />
          {t("audio.stop")}
        </button>
      </div>
    );
  }

  return (
    <div className="relative">
      <textarea
        className={cn(
          "min-h-24 w-full resize-none rounded-md border bg-background px-3 py-2 pr-10 text-sm outline-none transition-colors placeholder:text-muted-foreground focus:border-ring focus:ring-2 focus:ring-ring/20 disabled:opacity-50",
          className,
        )}
        disabled={busy}
        placeholder={isTranscribing ? t("audio.transcribing") : placeholder}
        value={value}
        onChange={(e) => onChange(e.target.value)}
      />

      <Button
        aria-label={isTranscribing ? t("audio.transcribing") : t("audio.record_note")}
        className="absolute bottom-2 right-2 size-7"
        disabled={busy}
        size="icon"
        type="button"
        variant="ghost"
        onClick={startRecording}
      >
        {isTranscribing ? (
          <Loader2 className="size-3.5 animate-spin" />
        ) : (
          <Mic className="size-3.5" />
        )}
      </Button>
    </div>
  );
}

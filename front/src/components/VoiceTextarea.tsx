import { useRef, useState } from "react";
import { Loader2, Mic, MicOff } from "lucide-react";

import { postTranscribe } from "@/api/ai";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

type VoiceTextareaProps = {
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
  className?: string;
  disabled?: boolean;
};

export function VoiceTextarea({ value, onChange, placeholder, className, disabled }: VoiceTextareaProps) {
  const [isRecording, setIsRecording] = useState(false);
  const [isTranscribing, setIsTranscribing] = useState(false);
  const [waveformBars, setWaveformBars] = useState<number[]>(Array(20).fill(0));

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
        setWaveformBars(Array(20).fill(0));
        setIsRecording(false);

        const blob = new Blob(chunksRef.current, { type: mimeType });
        chunksRef.current = [];
        setIsTranscribing(true);
        try {
          const text = await postTranscribe(blob);
          const trimmed = text.trim();
          if (trimmed) {
            onChange(value ? `${value} ${trimmed}` : trimmed);
          }
        } catch {
          // transcription failure non-critical
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

  const barH = (v: number) => Math.max(3, Math.min(16, v * 16));
  const busy = disabled || isTranscribing;

  return (
    <div className="relative">
      <textarea
        className={cn(
          "min-h-24 w-full resize-none rounded-md border bg-background px-3 py-2 pr-10 text-sm outline-none transition-colors placeholder:text-muted-foreground focus:border-ring focus:ring-2 focus:ring-ring/20 disabled:opacity-50",
          className,
        )}
        disabled={busy || isRecording}
        placeholder={isRecording ? undefined : placeholder}
        value={value}
        onChange={(e) => onChange(e.target.value)}
      />

      {/* Live waveform overlay while recording */}
      {isRecording && (
        <div className="absolute inset-0 flex items-center gap-px rounded-md border border-destructive bg-background px-3 pointer-events-none overflow-hidden">
          <span className="size-2 shrink-0 rounded-full bg-destructive animate-pulse mr-1" />
          {waveformBars.map((v, i) => (
            <div
              key={i}
              className="w-1 shrink-0 rounded-full bg-destructive"
              style={{ height: `${barH(v)}px` }}
            />
          ))}
        </div>
      )}

      {/* Mic / stop / spinner button */}
      <Button
        aria-label={isRecording ? "Parar grabación" : isTranscribing ? "Transcribiendo…" : "Grabar nota de voz"}
        className="absolute bottom-2 right-2 size-7"
        disabled={busy}
        size="icon"
        type="button"
        variant={isRecording ? "destructive" : "ghost"}
        onClick={isRecording ? stopRecording : startRecording}
      >
        {isTranscribing ? (
          <Loader2 className="size-3.5 animate-spin" />
        ) : isRecording ? (
          <MicOff className="size-3.5" />
        ) : (
          <Mic className="size-3.5" />
        )}
      </Button>
    </div>
  );
}

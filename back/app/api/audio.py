import asyncio

from elevenlabs.client import ElevenLabs
from fastapi import APIRouter, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from groq import Groq
from pydantic import BaseModel

from app.core.config import get_settings

router = APIRouter(prefix="/audio", tags=["audio"])

ELEVENLABS_VOICE_ID = "RwzBDEn5f6FIgpAjH9YN"


class SynthesizeRequest(BaseModel):
    text: str


@router.post("/transcribe")
async def transcribe(file: UploadFile) -> dict[str, str]:
    settings = get_settings()
    if not settings.groq_api_key:
        raise HTTPException(status_code=503, detail="STT not configured")

    audio_bytes = await file.read()
    filename = file.filename or "audio.webm"

    def _transcribe() -> str:
        client = Groq(api_key=settings.groq_api_key)
        transcription = client.audio.transcriptions.create(
            file=(filename, audio_bytes),
            model="whisper-large-v3",
            temperature=0,
            response_format="verbose_json",
        )
        return transcription.text

    text = await asyncio.to_thread(_transcribe)
    return {"text": text}


@router.post("/synthesize")
async def synthesize(body: SynthesizeRequest) -> StreamingResponse:
    settings = get_settings()
    if not settings.eleven_labs_api_key:
        raise HTTPException(status_code=503, detail="TTS not configured")

    def _synthesize() -> bytes:
        client = ElevenLabs(api_key=settings.eleven_labs_api_key)
        chunks = client.text_to_speech.convert(
            voice_id=ELEVENLABS_VOICE_ID,
            text=body.text,
        )
        return b"".join(chunks)

    audio_bytes = await asyncio.to_thread(_synthesize)

    return StreamingResponse(
        iter([audio_bytes]),
        media_type="audio/mpeg",
        headers={"Content-Length": str(len(audio_bytes))},
    )

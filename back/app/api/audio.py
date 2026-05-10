import asyncio
import io

import assemblyai as aai
from elevenlabs.client import ElevenLabs
from fastapi import APIRouter, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.core.config import get_settings

router = APIRouter(prefix="/audio", tags=["audio"])

ELEVENLABS_VOICE_ID = "RwzBDEn5f6FIgpAjH9YN"
ELEVENLABS_MODEL = "eleven_multilingual_v2"


class SynthesizeRequest(BaseModel):
    text: str
    lang: str = "es"


@router.post("/transcribe")
async def transcribe(file: UploadFile) -> dict[str, str]:
    settings = get_settings()
    if not settings.assemblyai_api_key:
        raise HTTPException(status_code=503, detail="STT not configured")

    audio_bytes = await file.read()

    def _transcribe() -> str:
        aai.settings.api_key = settings.assemblyai_api_key
        config = aai.TranscriptionConfig(
            speech_models=["universal-3-pro", "universal-2"],
            language_detection=True,
        )
        transcript = aai.Transcriber(config=config).transcribe(io.BytesIO(audio_bytes))
        if transcript.status == aai.TranscriptStatus.error:
            raise RuntimeError(transcript.error)
        return transcript.text or ""

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
            model_id=ELEVENLABS_MODEL,
            language_code=body.lang,
        )
        return b"".join(chunks)

    audio_bytes = await asyncio.to_thread(_synthesize)

    return StreamingResponse(
        iter([audio_bytes]),
        media_type="audio/mpeg",
        headers={"Content-Length": str(len(audio_bytes))},
    )

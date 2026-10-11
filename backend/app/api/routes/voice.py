"""Voice integration status endpoints."""

from fastapi import APIRouter, Depends

from app.core.config import Settings, get_settings
from app.schemas.voice import VoiceStatusResponse
from app.services.elevenlabs_service import ElevenLabsService

router = APIRouter()


@router.get("/voice/status", response_model=VoiceStatusResponse)
async def voice_status(
    settings: Settings = Depends(get_settings),
) -> VoiceStatusResponse:
    configured, message = ElevenLabsService(settings).configuration_status()
    return VoiceStatusResponse(configured=configured, message=message)

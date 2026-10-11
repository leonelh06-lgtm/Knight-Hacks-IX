"""Placeholder for the future ElevenLabs integration."""

from app.core.config import Settings


class ElevenLabsService:
    """Expose credential readiness without making external API requests."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def configuration_status(self) -> tuple[bool, str]:
        if self._settings.elevenlabs_credentials_configured:
            return (
                True,
                "Credentials are configured; ElevenLabs integration is not implemented yet",
            )
        return False, "ElevenLabs integration not configured yet"

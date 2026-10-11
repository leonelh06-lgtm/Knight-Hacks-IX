"""Voice API response schemas."""

from pydantic import BaseModel, ConfigDict


class VoiceStatusResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    configured: bool
    message: str

"""Environment-backed application settings."""

from functools import lru_cache
from urllib.parse import urlsplit

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Settings are optional by default so local startup needs no API secrets."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    elevenlabs_api_key: SecretStr | None = None
    elevenlabs_voice_id: SecretStr | None = None
    elevenlabs_model_id: str = "eleven_multilingual_v2"
    app_env: str = "development"
    cors_origins: list[str] = Field(
        default_factory=lambda: [
            "http://localhost:3000",
            "http://127.0.0.1:3000",
            "http://localhost:5173",
            "http://127.0.0.1:5173",
        ]
    )

    @field_validator("cors_origins")
    @classmethod
    def validate_cors_origins(cls, origins: list[str]) -> list[str]:
        for origin in origins:
            parsed = urlsplit(origin)
            if (
                origin == "*"
                or parsed.scheme not in {"http", "https"}
                or not parsed.netloc
                or parsed.path
                or parsed.query
                or parsed.fragment
                or parsed.username is not None
                or parsed.password is not None
            ):
                raise ValueError(f"Invalid CORS origin: {origin!r}")
        return origins

    @property
    def elevenlabs_credentials_configured(self) -> bool:
        api_key = self.elevenlabs_api_key
        voice_id = self.elevenlabs_voice_id
        return bool(
            api_key
            and api_key.get_secret_value().strip()
            and voice_id
            and voice_id.get_secret_value().strip()
        )


@lru_cache
def get_settings() -> Settings:
    """Return one settings instance for the application process."""
    return Settings()

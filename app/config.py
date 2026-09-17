"""Centralized, validated configuration. Replaces the scattered os.getenv() calls
and the hardware-derived DB password from v1."""
import base64

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # --- Networking / TLS ---
    api_port: int = 2053
    tls_certfile: str = ".fullchain.pem"
    tls_keyfile: str = ".privkey.pem"
    cors_allowed_origins: list[str] = Field(default_factory=list)

    # --- Admin web UI ---
    # False only for local HTTP development (vite dev server without TLS).
    # Always True in any deployment reachable over the network.
    session_cookie_secure: bool = True

    # --- Database ---
    database_url: str = Field(..., description="postgresql+asyncpg://user:pass@host:port/db")

    # --- Redis (rate limiting + lockout + auth nonce state) ---
    redis_url: str = "redis://localhost:6379/0"

    # --- Cryptography ---
    # 32 random bytes, base64-encoded. Generate with:
    #   python -c "import secrets, base64; print(base64.b64encode(secrets.token_bytes(32)).decode())"
    master_key_b64: str = Field(..., description="Base64-encoded 32-byte master key")

    # --- TOTP ---
    totp_issuer: str = "Crypt Master"
    totp_window: int = 1

    # --- Lockout / throttling policy ---
    fail_threshold: int = 3
    fail_lockout_minutes: int = 60
    api_open_minutes: int = 5

    @field_validator("master_key_b64")
    @classmethod
    def _validate_master_key(cls, value: str) -> str:
        try:
            raw = base64.b64decode(value, validate=True)
        except Exception as exc:  # noqa: BLE001
            raise ValueError("master_key_b64 must be valid base64") from exc
        if len(raw) != 32:
            raise ValueError("master key must decode to exactly 32 bytes")
        return value

    @property
    def master_key(self) -> bytes:
        return base64.b64decode(self.master_key_b64)


settings = Settings()  # type: ignore[call-arg]

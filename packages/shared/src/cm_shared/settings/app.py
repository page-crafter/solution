from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class AppSettings(BaseSettings):
    """Read environment configuration used by the API and worker processes."""

    app_env: str = "local"
    web_origin: str = "http://localhost:5173"
    database_url: str = "postgresql+psycopg://confluence:confluence@localhost:5432/page_crafter"
    redis_url: str = "redis://localhost:6379/0"

    keycloak_url: str = "http://localhost:8080"
    keycloak_internal_url: str | None = None
    keycloak_realm: str = "page-crafter"
    keycloak_client_id: str = "page-crafter-web"
    keycloak_audience: str = "page-crafter-api"

    confluence_base_url: str = "http://localhost:8090"
    confluence_space_key: str = "DOC"
    confluence_pat: str = Field(default="", repr=False)
    confluence_api_timeout_seconds: int = 30

    llm_provider: str = "openai"
    openai_api_key: str = Field(default="", repr=False)
    openai_base_url: str = "https://api.openai.com/v1"
    openai_model: str = "gpt-4o"
    openai_embedding_model: str = "text-embedding-3-small"
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.1"
    ollama_embedding_model: str = "nomic-embed-text"

    lightrag_base_url: str = "http://localhost:9621"
    lightrag_api_key: str = Field(default="", repr=False)
    lightrag_chat_history_turns: int = 3
    lightrag_pipeline_timeout_seconds: int = 900

    sync_cron: str = "0 2 * * *"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    @property
    def effective_openai_api_key(self) -> str:
        """Return an OpenAI API key or a local placeholder for compatible endpoints."""
        if self.openai_api_key:
            return self.openai_api_key
        if self.openai_base_url.rstrip("/") != "https://api.openai.com/v1":
            return "not-needed"
        return ""

    @property
    def jwks_url(self) -> str:
        """Return the Keycloak JWKS endpoint used to validate bearer tokens."""
        keycloak_url = self.keycloak_internal_url or self.keycloak_url
        return f"{keycloak_url}/realms/{self.keycloak_realm}/protocol/openid-connect/certs"

    @property
    def issuer_url(self) -> str:
        """Return the issuer expected in Keycloak JWTs."""
        return f"{self.keycloak_url}/realms/{self.keycloak_realm}"


@lru_cache(maxsize=1)
def get_settings() -> AppSettings:
    """Return cached application settings loaded from environment variables."""
    return AppSettings()

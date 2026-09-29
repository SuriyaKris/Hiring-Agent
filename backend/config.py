"""
Config — reads .env and exposes typed settings.
LLM_PROVIDER switches between free (Groq) and paid (OpenAI).
"""
from pydantic import field_validator
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):

    database_url: str = (
        "postgresql+asyncpg://postgres:postgres@localhost:5432/hiring_agent"
    )

    @field_validator("database_url", mode="before")
    @classmethod
    def convert_database_url(cls, v):
        if isinstance(v, str) and v.startswith("postgresql://"):
            return v.replace(
                "postgresql://",
                "postgresql+asyncpg://",
                1
            )
        return v

    # LLM provider switch (primary: "gemini" | fallback: "groq" | optional: "openai")
    llm_provider: str = "gemini"

    # Gemini — Google AI Studio (primary free & high rate limit)
    gemini_api_key: str = ""
    gemini_fast_model: str = "gemini-3.5-flash-lite"
    gemini_smart_model: str = "gemini-3.5-flash-lite"

    # Groq — free tier fallback
    groq_api_key: str = ""
    groq_fast_model: str = "llama-3.1-8b-instant"
    groq_smart_model: str = "llama-3.3-70b-versatile"

    # OpenAI — optional paid production
    openai_api_key: str = ""
    openai_fast_model: str = "gpt-4o-mini"
    openai_smart_model: str = "gpt-4o"

    # Data sources
    apollo_api_key: str = ""            # blank = use mock data
    apollo_client_id: str = ""
    apollo_client_secret: str = ""
    apollo_redirect_uri: str = ""
    serpapi_key: str = ""
    proxycurl_api_key: str = ""

    # App credentials for browser agents
    linkedin_username: str = ""
    linkedin_password: str = ""
    indeed_username: str = ""
    indeed_password: str = ""

    # App
    app_env: str = "development"
    app_port: int = 8000
    frontend_url: str = "http://localhost:5173"

    # Database
    # Database


    # LangSmith (optional)
    langchain_tracing_v2: bool = False
    langchain_api_key: str = ""
    langchain_project: str = "hiring-agent-v2"

    @property
    def fast_model(self) -> str:
        """Return the fast model name for the active provider."""
        if self.llm_provider == "openai":
            return self.openai_fast_model
        elif self.llm_provider == "gemini":
            return self.gemini_fast_model
        return self.groq_fast_model

    @property
    def smart_model(self) -> str:
        """Return the smart model name for the active provider."""
        if self.llm_provider == "openai":
            return self.openai_smart_model
        elif self.llm_provider == "gemini":
            return self.gemini_smart_model
        return self.groq_smart_model

    @property
    def using_mock_data(self) -> bool:
        """Return True if Apollo API key is not configured."""
        return not bool(self.apollo_api_key and self.apollo_api_key.strip())


    class Config:
        env_file = ".env"
        extra = "ignore"


@lru_cache()
def get_settings() -> Settings:
    return Settings()

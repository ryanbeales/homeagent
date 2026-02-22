import os
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    irc_server: str = "localhost"
    irc_port: int = 6667
    irc_channel: str = "#agents"
    ollama_host: str = "http://localhost:11434"
    ollama_model: str = "gpt-oss:20b"
    searxng_url: str = "https://searxng.crobasaurusrex.ryanbeales.com/"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()

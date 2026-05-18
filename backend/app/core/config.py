from pydantic_settings import BaseSettings, SettingsConfigDict
from enum import Enum


class LLMMode(str, Enum):
    REAL = "real"
    MOCK = "mock"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )
    
    app_name: str = "DevTeam-AI"
    debug: bool = True
    
    llm_mode: LLMMode = LLMMode.REAL
    
    openai_api_key: str = ""
    openai_base_url: str = "https://api.openai.com/v1"
    
    deepseek_api_key: str = ""
    deepseek_base_url: str = "https://api.deepseek.com"
    deepseek_model: str = "deepseek-chat"
    
    anthropic_api_key: str = ""
    anthropic_base_url: str = "https://api.anthropic.com"
    
    azure_api_key: str = ""
    azure_endpoint: str = ""
    azure_api_version: str = "2024-02-15-preview"
    
    default_llm_provider: str = "deepseek"
    default_llm_model: str = "deepseek-chat"
    
    database_url: str = "sqlite+aiosqlite:///./data/devteam.db"
    
    max_tokens_per_request: int = 4000
    request_timeout: int = 120

    workspace_root: str = "../../devteam-workspaces"


def get_settings() -> Settings:
    settings = Settings()
    if settings.llm_mode == LLMMode.MOCK:
        settings.default_llm_provider = "mock"
        settings.default_llm_model = "mock-model"
    return settings

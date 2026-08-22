import os
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional

class Settings(BaseSettings):
    GROQ_API_KEY: Optional[str] = None
    GROQ_MODEL: Optional[str] = None
    OPENAI_API_KEY: Optional[str] = None
    LLM_MODEL: str = "openai/gpt-oss-120b"
    EMBEDDING_MODEL: str = "all-MiniLM-L6-v2"
    
    TAVILY_API_KEY: Optional[str] = None
    
    ENABLE_RERANKER: bool = False
    
    DATABASE_URL: str = "sqlite+aiosqlite:///./research_assistant.db"
    CHROMA_PERSIST_DIRECTORY: str = "./chroma_db"
    
    LANGCHAIN_TRACING_V2: bool = False
    LANGCHAIN_API_KEY: Optional[str] = None
    LANGCHAIN_PROJECT: str = "agentic-research-assistant"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()

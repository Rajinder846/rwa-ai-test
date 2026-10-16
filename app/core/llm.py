from functools import lru_cache

from langchain_google_genai import ChatGoogleGenerativeAI

from app.config.settings import settings
from app.core.logger import get_logger


logger = get_logger("llm")


@lru_cache
def get_llm() -> ChatGoogleGenerativeAI:
    """
    Create and cache the application's Gemini LLM provider.

    A single configured provider is reused throughout
    the AI platform.
    """

    logger.info(
        "initializing_llm",
        provider="google",
        model=settings.gemini_model,
    )

    return ChatGoogleGenerativeAI(
        model=settings.gemini_model,
        google_api_key=settings.google_api_key,
        temperature=settings.gemini_temperature,
        max_retries=settings.gemini_max_retries,
    )
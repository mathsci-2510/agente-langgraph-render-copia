# app/llm.py
"""Fábrica del LLM: OpenAI real o modelo simulado, según configuración."""
import logging

from langchain_core.language_models.chat_models import BaseChatModel

from . import config
from .simulated_llm import SimulatedChatModel

logger = logging.getLogger(__name__)


def resolve_mode() -> str:
    if config.AGENT_MODE == "openai":
        if not config.OPENAI_API_KEY:
            raise RuntimeError("AGENT_MODE=openai pero OPENAI_API_KEY está vacía.")
        return "openai"
    if config.AGENT_MODE == "simulado":
        return "simulado"
    return "openai" if config.OPENAI_API_KEY else "simulado"


def build_llm() -> BaseChatModel:
    mode = resolve_mode()
    if mode == "openai":
        from langchain_openai import ChatOpenAI

        logger.info("LLM: OpenAI (%s)", config.OPENAI_MODEL)
        return ChatOpenAI(model=config.OPENAI_MODEL, temperature=0.2, api_key=config.OPENAI_API_KEY)

    logger.info("LLM: modelo SIMULADO (sin API key, sin costo)")
    return SimulatedChatModel()

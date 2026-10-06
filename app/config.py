# app/config.py
"""Configuración leída desde variables de entorno (Render las inyecta en producción)."""
import os

from dotenv import load_dotenv

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip()
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

# "auto"      -> usa OpenAI si hay API key, si no usa el modelo simulado
# "simulado"  -> fuerza el modelo simulado (ideal para demos sin costo)
# "openai"    -> fuerza OpenAI (falla si no hay API key)
AGENT_MODE = os.getenv("AGENT_MODE", "auto").strip().lower()

APP_VERSION = os.getenv("APP_VERSION", "1.0.0")

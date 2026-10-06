# main.py
"""API del agente. Render la levanta con: uvicorn main:app --host 0.0.0.0 --port $PORT"""
import logging
import uuid
from pathlib import Path
from typing import List, Optional

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from langchain_core.messages import AIMessage, HumanMessage
from pydantic import BaseModel, Field

from app import config
from app.graph import graph
from app.llm import resolve_mode

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(name)s | %(message)s")
logger = logging.getLogger("agente")

app = FastAPI(title="Asesor de viajes – LangGraph demo", version=config.APP_VERSION)
STATIC_DIR = Path(__file__).parent / "static"


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, examples=["Hola, quiero un viaje de playa"])
    thread_id: Optional[str] = Field(None, description="Id de conversación; si no se envía se crea uno.")


class ChatResponse(BaseModel):
    reply: str
    thread_id: str
    mode: str
    tools_used: List[str]


@app.get("/health")
def health():
    return {"status": "ok", "mode": resolve_mode(), "version": config.APP_VERSION}


@app.post("/chat", response_model=ChatResponse)
async def chat(payload: ChatRequest):
    thread_id = payload.thread_id or uuid.uuid4().hex
    logger.info("POST /chat | thread=%s | msg=%s", thread_id, payload.message)

    try:
        result = await graph.ainvoke(
            {"messages": [HumanMessage(content=payload.message)]},
            config={"configurable": {"thread_id": thread_id}},
        )
    except Exception:
        logger.exception("Error ejecutando el grafo | thread=%s", thread_id)
        raise HTTPException(status_code=500, detail="El agente tuvo un problema procesando el mensaje.")

    messages = result["messages"]
    last_human = max(i for i, m in enumerate(messages) if isinstance(m, HumanMessage))
    tools_used = [
        call["name"]
        for m in messages[last_human:]
        if isinstance(m, AIMessage)
        for call in (m.tool_calls or [])
    ]

    return ChatResponse(
        reply=str(messages[-1].content),
        thread_id=thread_id,
        mode=resolve_mode(),
        tools_used=tools_used,
    )


@app.get("/", include_in_schema=False)
def index():
    return FileResponse(STATIC_DIR / "index.html")

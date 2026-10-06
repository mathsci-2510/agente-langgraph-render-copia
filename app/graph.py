# app/graph.py
"""
Grafo LangGraph del agente (patrón ReAct):

    START ──► agent ──(¿pidió tool?)──► tools ──┐
                 ▲          │ no                │
                 │          ▼                   │
                 │         END                  │
                 └──────────────────────────────┘

- agent: el LLM decide si responde o si llama una herramienta.
- tools: ejecuta la herramienta y devuelve el resultado al agente.
- checkpointer: guarda el historial por thread_id (memoria de la conversación).
"""
from typing import Annotated, TypedDict

from langchain_core.messages import AnyMessage, SystemMessage
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, tools_condition

from .llm import build_llm
from .prompts import SYSTEM_PROMPT
from .tools import TOOLS


class AgentState(TypedDict):
    messages: Annotated[list[AnyMessage], add_messages]


llm_with_tools = build_llm().bind_tools(TOOLS)


def agent_node(state: AgentState) -> dict:
    # El system prompt se antepone en cada turno pero NO se guarda en el historial:
    # así la memoria no crece con copias del prompt.
    messages = [SystemMessage(content=SYSTEM_PROMPT)] + state["messages"]
    response = llm_with_tools.invoke(messages)
    return {"messages": [response]}


def build_graph():
    builder = StateGraph(AgentState)
    builder.add_node("agent", agent_node)
    builder.add_node("tools", ToolNode(TOOLS))

    builder.add_edge(START, "agent")
    builder.add_conditional_edges("agent", tools_condition, {"tools": "tools", END: END})
    builder.add_edge("tools", "agent")

    # MemorySaver vive en RAM: suficiente para la demo. En producción real se cambia
    # por un checkpointer persistente (Redis, Postgres) para no perder conversaciones.
    return builder.compile(checkpointer=MemorySaver())


graph = build_graph()

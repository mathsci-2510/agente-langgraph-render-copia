# app/simulated_llm.py
"""
Modelo de chat SIMULADO que implementa la interfaz BaseChatModel de LangChain.

Para LangGraph es indistinguible de ChatOpenAI: recibe mensajes, devuelve AIMessage
y puede pedir tool_calls. Así el grafo, las tools y la memoria funcionan de verdad,
pero sin API key ni costo. Las respuestas salen de reglas simples que respetan el
system prompt (nombre del agente, agencia, una sola pregunta por mensaje).
"""
from __future__ import annotations

import ast
import json
import re
import unicodedata
import uuid
from typing import Any, List, Optional, Sequence

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_core.outputs import ChatGeneration, ChatResult

# Alias de texto -> destino que entiende la tool consultar_requisitos
_DESTINOS = {
    "galapagos": "Galápagos",
    "cusco": "Cusco", "machu picchu": "Cusco", "peru": "Perú",
    "cartagena": "Cartagena", "colombia": "Colombia",
    "cancun": "Cancún", "mexico": "México",
    "madrid": "Madrid", "barcelona": "Barcelona", "espana": "España", "europa": "España",
}
_REQUISITOS_WORDS = ("requisito", "documento", "visa", "pasaporte", "cedula", "necesito para")
_PAQUETES_WORDS = (
    "paquete", "destino", "viaje", "viajar", "precio", "cuesta", "cuanto", "playa",
    "vacaciones", "tour", "recomienda", "recomiendas", "conocer", "luna de miel", "cultura",
)
_GREETING_WORDS = ("hola", "buenas", "buenos dias", "buenas tardes", "buenas noches", "saludos")
_THANKS_WORDS = ("gracias", "chao", "adios", "hasta luego")
_NAME_RE = re.compile(r"(?i)\b(?:me llamo|mi nombre es)\s+([a-záéíóúñ]+)")


def _norm(texto: str) -> str:
    texto = unicodedata.normalize("NFKD", (texto or "").lower())
    return "".join(c for c in texto if not unicodedata.combining(c))


def _has_any(texto: str, palabras: Sequence[str]) -> bool:
    return any(p in texto for p in palabras)


def _find_destino(texto: str) -> Optional[str]:
    t = _norm(texto)
    return next((destino for alias, destino in _DESTINOS.items() if alias in t), None)


def _parse_tool_content(content: Any) -> Any:
    if not isinstance(content, str):
        return content
    for parser in (json.loads, ast.literal_eval):
        try:
            return parser(content)
        except Exception:
            continue
    return content


class SimulatedChatModel(BaseChatModel):
    """LLM de reglas que se comporta como un modelo con tool calling."""

    tool_names: List[str] = []

    @property
    def _llm_type(self) -> str:
        return "simulado"

    def bind_tools(self, tools: Sequence[Any], **kwargs: Any) -> "SimulatedChatModel":
        names = [getattr(t, "name", str(t)) for t in tools]
        return self.model_copy(update={"tool_names": names})

    # ------------------------------------------------------------------ helpers
    @staticmethod
    def _persona(messages: List[BaseMessage]) -> tuple[str, str]:
        system = next((m.content for m in messages if isinstance(m, SystemMessage)), "")
        agente = re.search(r"Te llamas (\w+)", system)
        agencia = re.search(r"asesora? de viajes de ([^\n.]+)", system)
        return (agente.group(1) if agente else "tu asesora",
                agencia.group(1).strip() if agencia else "la agencia")

    @staticmethod
    def _user_name(messages: List[BaseMessage]) -> Optional[str]:
        nombre = None
        for m in messages:
            if isinstance(m, HumanMessage):
                found = _NAME_RE.search(m.content)
                if found:
                    nombre = found.group(1).capitalize()
        return nombre

    @staticmethod
    def _last_destino_in_history(messages: List[BaseMessage]) -> Optional[str]:
        """Memoria: si el cliente no dice el destino, usa el último que mencionó."""
        for m in reversed(messages):
            if isinstance(m, HumanMessage):
                destino = _find_destino(m.content)
                if destino:
                    return destino
        return None

    def _tool_call(self, name: str, args: dict) -> Optional[AIMessage]:
        if name not in self.tool_names:
            return None
        return AIMessage(
            content="",
            tool_calls=[{"name": name, "args": args, "id": f"call_{uuid.uuid4().hex[:12]}"}],
        )

    # ------------------------------------------------------------- respuestas
    def _answer_from_tool(self, msg: ToolMessage, nombre: Optional[str]) -> AIMessage:
        data = _parse_tool_content(msg.content)
        inicio = f"¡Claro, {nombre}! " if nombre else "¡Claro! "

        if msg.name == "buscar_paquetes" and isinstance(data, list):
            lineas = [f"• {p['destino']} ({p['pais']}), {p['dias']} días: desde ${p['precio_desde_usd']:,} USD."
                      for p in data[:3]]
            texto = inicio + "Estos paquetes te pueden encantar:\n" + "\n".join(lineas)
            return AIMessage(content=texto + "\n¿Cuál de estos destinos te llama más la atención?")

        if msg.name == "consultar_requisitos" and isinstance(data, dict):
            if not data.get("pais"):
                return AIMessage(content=f"{data['requisitos']}\n¿Te gustaría ver los destinos que sí tenemos?")
            return AIMessage(content=(
                f"{inicio}Para viajar a {data['destino']} ({data['pais']}) necesitas: {data['requisitos']}\n"
                "Son requisitos referenciales; el asesor los confirma al reservar. ¿Te ayudo a cotizar ese viaje?"
            ))

        return AIMessage(content=f"{inicio}¿Te ayudo con algo más?")

    def _answer_from_user(self, texto: str, messages: List[BaseMessage]) -> AIMessage:
        agente, agencia = self._persona(messages)
        nombre = self._user_name(messages)
        t = _norm(texto)

        if "como me llamo" in t or "cual es mi nombre" in t or "sabes mi nombre" in t:
            if nombre:
                return AIMessage(content=f"Te llamas {nombre}, lo tengo presente. ¿A dónde te gustaría viajar?")
            return AIMessage(content="Todavía no me lo has dicho. ¿Cómo te llamas?")

        if _NAME_RE.search(texto) and not _has_any(t, _PAQUETES_WORDS + _REQUISITOS_WORDS):
            return AIMessage(content=f"Mucho gusto, {nombre}. ¿Qué tipo de viaje tienes en mente: playa, cultura o aventura?")

        if _has_any(t, _REQUISITOS_WORDS):
            destino = _find_destino(texto) or self._last_destino_in_history(messages)
            if not destino:
                return AIMessage(content="Con gusto te ayudo con los requisitos. ¿A qué destino quieres viajar?")
            call = self._tool_call("consultar_requisitos", {"destino": destino})
            if call:
                return call

        if _has_any(t, _PAQUETES_WORDS) or _find_destino(texto):
            # Como haría un LLM real: si identifica el destino, busca por él
            call = self._tool_call("buscar_paquetes", {"consulta": _find_destino(texto) or texto})
            if call:
                return call

        if _has_any(t, _GREETING_WORDS):
            return AIMessage(content=(
                f"¡Hola! Soy {agente}, asesora de viajes de {agencia}. "
                "¿A dónde sueñas viajar?"
            ))

        if _has_any(t, _THANKS_WORDS):
            fin = f", {nombre}" if nombre else ""
            return AIMessage(content=f"¡Con gusto{fin}! Aquí estaré para tu próximo viaje. ¿Te ayudo con algo más?")

        return AIMessage(content=(
            "Puedo ayudarte a elegir destino, ver paquetes con precios y revisar requisitos de viaje. "
            "¿Qué te gustaría saber?"
        ))

    # ------------------------------------------------------- interfaz LangChain
    def _generate(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Any = None,
        **kwargs: Any,
    ) -> ChatResult:
        last = messages[-1]
        if isinstance(last, ToolMessage):
            reply = self._answer_from_tool(last, self._user_name(messages))
        else:
            reply = self._answer_from_user(str(last.content), messages)
        return ChatResult(generations=[ChatGeneration(message=reply)])

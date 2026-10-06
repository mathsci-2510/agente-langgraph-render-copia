# tests/test_agente.py
"""Tests end-to-end de la API usando el modelo simulado (no requieren API key)."""
import os

os.environ["AGENT_MODE"] = "simulado"

from fastapi.testclient import TestClient  # noqa: E402

from main import app  # noqa: E402

client = TestClient(app)


def chat(message: str, thread_id: str | None = None) -> dict:
    res = client.post("/chat", json={"message": message, "thread_id": thread_id})
    assert res.status_code == 200, res.text
    return res.json()


def test_health():
    data = client.get("/health").json()
    assert data["status"] == "ok"
    assert data["mode"] == "simulado"


def test_saludo_sigue_el_prompt():
    data = chat("Hola")
    assert "Sofía" in data["reply"]
    assert "Rumbo Viajes" in data["reply"]
    assert data["tools_used"] == []


def test_una_sola_pregunta_por_mensaje():
    for msg in ["Hola", "Quiero un viaje de playa", "Me llamo Ana", "gracias"]:
        assert chat(msg)["reply"].count("?") <= 1, msg


def test_busqueda_de_paquetes_usa_tool():
    data = chat("Quiero un viaje de playa")
    assert data["tools_used"] == ["buscar_paquetes"]
    assert "Cartagena" in data["reply"] or "Cancún" in data["reply"]
    assert "USD" in data["reply"]


def test_precio_de_destino_especifico():
    data = chat("¿Cuánto cuesta Cancún?")
    assert data["tools_used"] == ["buscar_paquetes"]
    assert data["reply"].splitlines()[1].startswith("• Cancún")


def test_requisitos_usa_tool():
    data = chat("¿Qué requisitos necesito para ir a México?")
    assert data["tools_used"] == ["consultar_requisitos"]
    assert "visa" in data["reply"].lower()


def test_memoria_recuerda_nombre_y_destino():
    tid = chat("Me llamo Ana")["thread_id"]
    chat("¿Cuánto cuesta Cusco?", tid)
    # No repite el destino: el agente lo toma de la memoria del thread
    data = chat("¿Qué documentos necesito?", tid)
    assert data["tools_used"] == ["consultar_requisitos"]
    assert "Perú" in data["reply"]
    assert "Ana" in chat("¿Cómo me llamo?", tid)["reply"]


def test_threads_aislados():
    chat("Me llamo Carlos", "thread-a")
    data = chat("¿Cómo me llamo?", "thread-b")
    assert "Carlos" not in data["reply"]

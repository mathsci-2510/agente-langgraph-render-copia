# app/tools.py
"""Herramientas (tools) que el agente puede invocar. Son funciones Python normales
decoradas con @tool de LangChain: el docstring es lo que el LLM lee para decidir usarlas.

Los datos son de EJEMPLO para la demo. En un agente real vendrían de una base de datos
o de la API de un proveedor."""
import re
import unicodedata
from typing import Dict, List

from langchain_core.tools import tool

PAQUETES: List[Dict] = [
    {"destino": "Galápagos", "pais": "Ecuador", "tipo": "naturaleza playa crucero islas",
     "dias": 5, "precio_desde_usd": 1450,
     "incluye": "vuelo desde Guayaquil, hotel en Santa Cruz y tours a islas."},
    {"destino": "Cusco y Machu Picchu", "pais": "Perú", "tipo": "cultura historia montaña aventura",
     "dias": 6, "precio_desde_usd": 1190,
     "incluye": "vuelos, hoteles, tren a Aguas Calientes y entrada a Machu Picchu."},
    {"destino": "Cartagena", "pais": "Colombia", "tipo": "playa caribe ciudad historica",
     "dias": 5, "precio_desde_usd": 890,
     "incluye": "vuelos, hotel en ciudad amurallada y paseo a Islas del Rosario."},
    {"destino": "Cancún", "pais": "México", "tipo": "playa caribe todo incluido resort",
     "dias": 7, "precio_desde_usd": 1650,
     "incluye": "vuelos, resort todo incluido y traslados."},
    {"destino": "Madrid y Barcelona", "pais": "España", "tipo": "europa ciudad cultura gastronomia",
     "dias": 10, "precio_desde_usd": 2890,
     "incluye": "vuelos, hoteles 4*, tren de alta velocidad y city tours."},
]

# Requisitos REFERENCIALES para viajeros ecuatorianos (datos de demo, verificar siempre)
REQUISITOS: Dict[str, str] = {
    "Ecuador": "Cédula de identidad. Para Galápagos: Tarjeta de Control de Tránsito y tasa de ingreso al parque.",
    "Perú": "Cédula de identidad vigente (Comunidad Andina) o pasaporte.",
    "Colombia": "Cédula de identidad vigente (Comunidad Andina) o pasaporte.",
    "México": "Pasaporte vigente y visa mexicana (o visa válida de EE. UU.).",
    "España": "Pasaporte vigente, visa Schengen, seguro de viaje y reserva de hotel.",
}


def _norm(texto: str) -> str:
    texto = unicodedata.normalize("NFKD", (texto or "").lower())
    return "".join(c for c in texto if not unicodedata.combining(c))


@tool
def buscar_paquetes(consulta: str) -> List[Dict]:
    """Busca paquetes turísticos de Rumbo Viajes por destino, país o tipo de viaje
    (playa, cultura, aventura, Europa...). Úsala cuando el cliente pregunte por
    destinos, paquetes, precios o recomendaciones de viaje."""
    palabras = [p for p in re.findall(r"\w+", _norm(consulta)) if len(p) > 3]
    resultados = []
    for p in PAQUETES:
        texto = _norm(f"{p['destino']} {p['pais']} {p['tipo']} {p['incluye']}")
        puntaje = sum(1 for w in palabras if w in texto)
        if puntaje:
            resultados.append((puntaje, p))
    resultados.sort(key=lambda x: x[0], reverse=True)
    # Sin coincidencias: devolvemos los destinos más vendidos para orientar
    return [p for _, p in resultados[:3]] or PAQUETES[:3]


@tool
def consultar_requisitos(destino: str) -> Dict:
    """Devuelve los documentos y requisitos de viaje para un destino o país.
    Úsala cuando el cliente pregunte por visa, pasaporte, documentos o requisitos."""
    d = _norm(destino)
    for p in PAQUETES:
        if _norm(p["destino"]) in d or _norm(p["pais"]) in d or d in _norm(p["destino"]):
            return {"destino": p["destino"], "pais": p["pais"], "requisitos": REQUISITOS[p["pais"]]}
    return {"destino": destino, "pais": None,
            "requisitos": "No tengo ese destino registrado; un asesor confirmará los requisitos."}


TOOLS = [buscar_paquetes, consultar_requisitos]

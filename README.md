# Agente asesor de viajes con LangGraph y despliegue en Render

Agente conversacional de ejemplo ("Sofía", asesora de **Rumbo Viajes**) construido con
**LangGraph + LangChain + FastAPI**, listo para subirse a GitHub y desplegarse en **Render**.

**Funciona sin API key.** Si no hay `OPENAI_API_KEY`, usa un *modelo simulado* que
implementa la misma interfaz de LangChain que `ChatOpenAI`. El grafo, las herramientas
(tools) y la memoria funcionan igual, pero sin costo. Si agregas una key, el mismo código
pasa a usar GPT sin cambiar nada más.

---

## Qué hace el agente

| Capacidad | Cómo se implementa |
|---|---|
| Sigue un system prompt (nombre, tono, una pregunta por mensaje) | `app/prompts.py` |
| Busca paquetes turísticos y precios | tool `buscar_paquetes` en `app/tools.py` |
| Consulta requisitos de viaje (visa, pasaporte) | tool `consultar_requisitos` en `app/tools.py` |
| Recuerda el nombre del cliente y el destino del que habló | checkpointer de LangGraph por `thread_id` |
| API HTTP + interfaz de chat web | `main.py` + `static/index.html` |

## Arquitectura

```
Navegador / cliente HTTP
        │  POST /chat {message, thread_id}
        ▼
   FastAPI (main.py)
        │  graph.ainvoke(...)
        ▼
 ┌──────────── LangGraph (app/graph.py) ────────────┐
 │  START ─► agent ──¿pidió tool?──► tools ─┐      │
 │             ▲          │ no              │      │
 │             │          ▼                 │      │
 │             │         END                │      │
 │             └────────────────────────────┘      │
 │  agent = LLM (OpenAI o simulado) + system prompt │
 │  memoria = MemorySaver por thread_id             │
 └──────────────────────────────────────────────────┘
```

## Estructura del repo

```
agente-langgraph-render/
├── app/
│   ├── config.py          # variables de entorno
│   ├── prompts.py         # system prompt del agente
│   ├── tools.py           # herramientas (@tool) y datos de ejemplo
│   ├── simulated_llm.py   # LLM simulado (BaseChatModel de LangChain)
│   ├── llm.py             # elige OpenAI o simulado
│   └── graph.py           # grafo LangGraph
├── static/index.html      # interfaz de chat
├── tests/test_agente.py   # tests end-to-end (sin API key)
├── main.py                # API FastAPI
├── requirements.txt       # dependencias de producción (versiones fijadas)
├── requirements-dev.txt   # + pytest
├── render.yaml            # Blueprint de Render (infraestructura como código)
└── .env.example           # plantilla de variables de entorno
```

---

## 1. Correrlo en tu computadora

Requisitos: **Python 3.11 o superior** y **Git**.

```bash
git clone https://github.com/<tu-usuario>/agente-langgraph-render.git
cd agente-langgraph-render

python -m venv .venv
# Windows (PowerShell):
.venv\Scripts\Activate.ps1
# macOS / Linux:
source .venv/bin/activate

pip install -r requirements-dev.txt
cp .env.example .env          # en Windows: copy .env.example .env

uvicorn main:app --reload
```

Abre:
- **http://127.0.0.1:8000**: interfaz de chat
- **http://127.0.0.1:8000/docs**: documentación interactiva de la API (Swagger)
- **http://127.0.0.1:8000/health**: estado y modo del LLM

Tests:

```bash
pytest -q
```

Prueba por línea de comandos:

```bash
curl -X POST http://127.0.0.1:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Quiero un viaje de playa", "thread_id": "demo"}'
```

---

## 2. Subirlo a GitHub

1. Entra a <https://github.com/new>.
2. Nombre: `agente-langgraph-render`, visibilidad **Public** o **Private** (Render acepta ambas).
3. **No** marques "Add a README", ".gitignore" ni "license": el repo ya los tiene.
4. Pulsa **Create repository** y, desde la carpeta del proyecto, ejecuta:

```bash
git remote add origin https://github.com/<tu-usuario>/agente-langgraph-render.git
git branch -M main
git push -u origin main
```

> La primera vez, Git pedirá iniciar sesión en GitHub. En Windows se abre una ventana
> del navegador (Git Credential Manager). En macOS/Linux usa un
> [Personal Access Token](https://github.com/settings/tokens) como contraseña.

> El archivo `.env` está en `.gitignore`: **las claves nunca se suben al repo**.

---

## 3. Desplegarlo en Render (como alguien externo que lo pone en producción)

Si el repo es de otra persona, primero haz **Fork** en GitHub (botón arriba a la derecha)
para tener tu propia copia. Render despliega desde *tu* cuenta de GitHub.

### Opción A: Blueprint (recomendada, usa `render.yaml`)

1. Crea una cuenta en <https://render.com> (puedes entrar con GitHub).
2. **New +** → **Blueprint**.
3. Conecta tu cuenta de GitHub y elige el repo `agente-langgraph-render`.
4. Render lee `render.yaml` y muestra el servicio `agente-viajes`.
5. Te pedirá `OPENAI_API_KEY` (marcada `sync: false`):
   - **Déjala vacía** para el modo simulado (demo gratis).
   - O pega tu key para usar GPT.
6. **Apply** / **Deploy Blueprint**.

### Opción B: Web Service manual

1. **New +** → **Web Service** → elige el repo.
2. Configura:

| Campo | Valor |
|---|---|
| Language | `Python 3` |
| Branch | `main` |
| Build Command | `pip install -r requirements.txt` |
| Start Command | `uvicorn main:app --host 0.0.0.0 --port $PORT` |
| Instance Type | `Free` |

3. En **Environment Variables** agrega `PYTHON_VERSION = 3.12.8` y, si quieres, `AGENT_MODE = auto`.
4. En **Advanced → Health Check Path** pon `/health`.
5. **Create Web Service**.

### Verificar el despliegue

- En la pestaña **Logs** verás la instalación y luego `Uvicorn running on http://0.0.0.0:XXXX`.
- Render te da una URL como `https://agente-viajes.onrender.com`:
  - `https://agente-viajes.onrender.com/`: chat
  - `https://agente-viajes.onrender.com/health`: debe responder `{"status":"ok", ...}`
  - `https://agente-viajes.onrender.com/docs`: API

### Ciclo de actualización (CI/CD)

Cada `git push` a `main` dispara un nuevo deploy automático:

```bash
# ejemplo: cambiar el nombre del agente
#   en app/prompts.py:  "Te llamas Sofía" -> "Te llamas Mateo"
git add .
git commit -m "Cambia el nombre del agente"
git push
```

En 1–3 minutos la URL pública responde con el cambio. Si un deploy falla, Render
mantiene la versión anterior en línea y puedes volver atrás desde **Events → Rollback**.

### Pasar a un LLM real

Render → tu servicio → **Environment** → agrega `OPENAI_API_KEY` → **Save, rebuild and deploy**.
`/health` mostrará `"mode": "openai"`. Para volver al simulado, borra la key o pon `AGENT_MODE=simulado`.

---

## Notas para producción real

- **Plan Free:** el servicio se apaga tras 15 min sin tráfico y la primera petición tarda ~1 min
  en despertar. Para una demo en vivo, abre `/health` unos minutos antes.
- **Memoria:** `MemorySaver` vive en RAM. Se pierde al reiniciar o redeployar, y no se comparte
  entre instancias. En producción se cambia por un checkpointer persistente
  (`langgraph-checkpoint-postgres` o `langgraph-checkpoint-redis`).
- **Secretos:** solo en variables de entorno de Render, nunca en el código.
- **Datos:** los paquetes y requisitos de `app/tools.py` son de ejemplo; en un caso real vendrían
  de una base de datos o API.

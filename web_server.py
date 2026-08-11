"""
MAGI System Web Server
API FastAPI que integra com magi_core.py
"""

import asyncio
import json
from fastapi import FastAPI, WebSocket, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path
import logging

from config import MagiConfig
from magi_core import MagiSystem

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# FastAPI App
app = FastAPI(
    title="MAGI System API",
    description="Multi-Agent AI Governance Interface",
    version="2.1",
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static files
static_dir = Path(__file__).parent / "static"
static_dir.mkdir(exist_ok=True)

if (static_dir / "index.html").exists():
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

# MAGI System initialization
try:
    config = MagiConfig()
    config.validate()
    magi_system = MagiSystem(config)
    logger.info("✅ MAGI System initialized successfully")
except ValueError as e:
    logger.error(f"❌ MAGI System initialization failed: {e}")
    magi_system = None


# ============================================================================
# REST API Endpoints
# ============================================================================


@app.get("/")
async def root():
    """Serve index.html"""
    index_path = static_dir / "index.html"
    if index_path.exists():
        return FileResponse(index_path)
    return {"message": "MAGI System Web Interface"}


@app.get("/api/health")
async def health():
    """Health check"""
    return {
        "status": "healthy",
        "magi_initialized": magi_system is not None,
        "api_version": "2.1",
    }


def _serialize(query: str, result) -> dict:
    """Converte um ConsensusResult no payload JSON da API.

    Expõe o resultado completo do motor de consenso — posições, quórum, veto e
    fontes. Sem isso um veredito vetado chega ao cliente como um CODE_RED
    genérico, sem dizer por quê.
    """
    return {
        "success": True,
        "query": query,
        "verdict": result.verdict.value,
        "consensus_rate": round(result.consensus_rate, 3),
        "reasoning": result.reasoning,
        "stances": {agente: s.value for agente, s in result.stances.items()},
        "live_agents": result.live_agents,
        "degraded": result.live_agents < 3,
        "vetoed": result.vetoed,
        "perspectives": {
            "melchior": result.melchior_response,
            "balthasar": result.balthasar_response,
            "gaspar": result.gaspar_response,
        },
        "sources": result.sources,
        "synthesis": result.final_recommendation,
    }


@app.post("/api/deliberate")
async def deliberate_endpoint(request_body: dict):
    """
    Deliberate sobre uma questão
    Body: {"query": "sua questão aqui"}
    """
    if not magi_system:
        raise HTTPException(status_code=503, detail="MAGI System not initialized")

    query = request_body.get("query", "").strip()
    if not query:
        raise HTTPException(status_code=400, detail="Query cannot be empty")

    try:
        logger.info(f"📋 Deliberating on: {query[:50]}...")
        result = await magi_system.deliberate(query)

        return _serialize(query, result)
    except Exception as e:
        logger.error(f"❌ Deliberation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/config")
async def get_config():
    """Retorna configuração do sistema"""
    if not magi_system:
        raise HTTPException(status_code=503, detail="MAGI System not initialized")

    return {
        "models": {
            "melchior": {
                "name": "Anthropic Claude",
                "model": magi_system.config.MELCHIOR_MODEL,
                "type": "scientific",
                "web_search": magi_system.config.ENABLE_WEB_SEARCH,
            },
            "balthasar": {
                "name": "Google Gemini",
                "model": magi_system.config.BALTHASAR_MODEL,
                "type": "ethical",
                "veto_power": True,
            },
            "gaspar": {
                "name": "Groq Llama",
                "model": magi_system.config.GASPAR_MODEL,
                "type": "practical",
            },
        },
        "judge": {
            "name": "Groq GPT-OSS",
            "model": magi_system.config.JUDGE_MODEL,
            "role": "classifica as posições — família distinta dos 3 agentes",
        },
        "thresholds": {
            "consensus": magi_system.config.CONSENSUS_THRESHOLD,
            "divergence": magi_system.config.DIVERGENCE_THRESHOLD,
        },
        "temperature": magi_system.config.TEMPERATURE,
    }


# ============================================================================
# WebSocket for Real-time Updates (Experimental)
# ============================================================================


@app.websocket("/ws/deliberate")
async def websocket_deliberate(websocket: WebSocket):
    """
    WebSocket para deliberação em tempo real
    Recebe: {"query": "sua questão"}
    Envia: updates parciais durante o processamento
    """
    await websocket.accept()
    logger.info("📡 WebSocket client connected")

    try:
        while True:
            data = await websocket.receive_text()
            request = json.loads(data)
            query = request.get("query", "").strip()

            if not query:
                await websocket.send_json(
                    {"error": "Query cannot be empty"}
                )
                continue

            if not magi_system:
                await websocket.send_json(
                    {"error": "MAGI System not initialized"}
                )
                continue

            try:
                # Send processing started
                await websocket.send_json(
                    {
                        "status": "processing",
                        "message": "Consultando MELCHIOR...",
                    }
                )

                # Call agents
                result = await magi_system.deliberate(query)

                # Send final result — mesmo payload da API REST
                await websocket.send_json(
                    {"status": "complete", **_serialize(query, result)}
                )

            except Exception as e:
                await websocket.send_json(
                    {
                        "status": "error",
                        "error": str(e),
                    }
                )

    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        logger.info("📡 WebSocket client disconnected")


# ============================================================================
# Server Info
# ============================================================================


@app.get("/api/info")
async def info():
    """Informações do sistema"""
    return {
        "name": "MAGI System",
        "version": "2.1",
        "description": "Multi-Agent AI Governance Interface",
        "agents": {
            "melchior": "Scientific (Claude + web search)",
            "balthasar": "Ethical (Gemini) — poder de veto",
            "gaspar": "Practical (Groq Llama)",
        },
        "endpoints": {
            "rest": "/api/deliberate (POST)",
            "websocket": "/ws/deliberate",
            "health": "/api/health (GET)",
            "config": "/api/config (GET)",
        },
    }


# ============================================================================
# Run Server
# ============================================================================


if __name__ == "__main__":
    import uvicorn

    print(
        """
╔════════════════════════════════════════════════════════════╗
║                                                            ║
║         ███╗   ███╗ █████╗  ██████╗ ██╗                   ║
║         ████╗ ████║██╔══██╗██╔════╝ ██║                   ║
║         ██╔████╔██║███████║██║  ███╗██║                   ║
║         ██║╚██╔╝██║██╔══██║██║   ██║██║                   ║
║         ██║ ╚═╝ ██║██║  ██║╚██████╔╝██║                   ║
║         ╚═╝     ╚═╝╚═╝  ╚═╝ ╚═════╝ ╚═╝                   ║
║                                                            ║
║           MULTI-AGENT AI GOVERNANCE INTERFACE              ║
║                  Web Server v2.1                           ║
║                                                            ║
╚════════════════════════════════════════════════════════════╝

🌐 Servidor iniciando em http://localhost:8000
📡 WebSocket em ws://localhost:8000/ws/deliberate
📚 Documentação: http://localhost:8000/docs
    """
    )

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info",
    )

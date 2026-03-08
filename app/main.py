"""
Azure AI Foundry - Document Management Application
====================================================
Main FastAPI application entry point.

AI-102 Certification coverage:
  ✅ Azure AI Document Intelligence (Form Recognizer)
  ✅ Azure AI Language (NLP, Sentiment, NER, PII, Summarization)
  ✅ Azure OpenAI Service (GPT-4o chat, RAG, document generation)
  ✅ Azure AI Vision (Image analysis, OCR)
  ✅ Azure AI Translator (Multi-language translation)
  ✅ Azure AI Content Safety (Content moderation)
  ✅ Azure AI Search (Semantic & vector search)
"""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from azure.core.exceptions import HttpResponseError
import os

from app.config import get_settings
from app.models.schemas import HealthResponse
from app.routers import documents, analysis, search

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: startup and shutdown events."""
    settings = get_settings()
    logger.info(
        "Starting Azure AI Foundry Document Management App (env: %s)", settings.app_env
    )
    # Ensure uploads directory exists
    os.makedirs("uploads", exist_ok=True)
    yield
    logger.info("Shutting down application")


app = FastAPI(
    title="Azure AI Foundry - Document Management",
    description="""
## Gestion Intelligente de Documents avec Azure AI Foundry

Application de référence pour la certification **Microsoft AI-102**.

### Services Azure AI intégrés

| Service | Fonctionnalités |
|---------|----------------|
| **Document Intelligence** | Extraction de texte, formulaires, factures, reçus, pièces d'identité |
| **Azure AI Language** | Détection de langue, sentiment, entités (NER), PII, résumé |
| **Azure OpenAI** | Q&A sur documents (RAG), génération, classification |
| **Azure AI Vision** | Analyse d'images, OCR, légendes, détection d'objets |
| **Azure AI Translator** | Traduction multilingue, translitération, dictionnaire |
| **Azure AI Content Safety** | Modération de contenu (Haine, Violence, Sexuel, Automutilation) |
| **Azure AI Search** | Recherche sémantique, vectorielle, filtres, facettes |

### Pipeline complet
`POST /analysis/analyze-file` — Analyse complète d'un document en une seule requête.
    """,
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

@app.exception_handler(HttpResponseError)
async def azure_http_error_handler(request: Request, exc: HttpResponseError):
    status = exc.status_code if exc.status_code else 502
    return JSONResponse(status_code=status, content={"detail": exc.message or str(exc)})


@app.exception_handler(Exception)
async def generic_error_handler(request: Request, exc: Exception):
    if isinstance(exc, HTTPException):
        raise exc
    logger.exception("Unhandled error on %s: %s", request.url.path, exc)
    return JSONResponse(status_code=500, content={"detail": str(exc)})


# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API Routers
app.include_router(documents.router, prefix="/api/v1")
app.include_router(analysis.router, prefix="/api/v1")
app.include_router(search.router, prefix="/api/v1")

# Serve frontend static files
frontend_dir = os.path.join(os.path.dirname(__file__), "..", "frontend")
if os.path.exists(frontend_dir):
    app.mount("/static", StaticFiles(directory=frontend_dir), name="static")


@app.get("/", include_in_schema=False)
async def serve_frontend():
    """Serve the frontend HTML application."""
    index_path = os.path.join(frontend_dir, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return JSONResponse({"message": "Azure AI Foundry Document Management API", "docs": "/docs"})


@app.get(
    "/health",
    response_model=HealthResponse,
    tags=["Health"],
    summary="Health check",
    description="Check the health status of all Azure AI services.",
)
async def health_check():
    """
    Health check endpoint.
    Verifies configuration for all Azure AI services.
    """
    settings = get_settings()

    def check_service(endpoint: str, key: str) -> str:
        if endpoint and key and endpoint != "" and key != "":
            return "configured"
        return "not_configured"

    services = {
        "document_intelligence": check_service(
            settings.azure_document_intelligence_endpoint,
            settings.azure_document_intelligence_key,
        ),
        "ai_language": check_service(
            settings.azure_language_endpoint, settings.azure_language_key
        ),
        "azure_openai": check_service(
            settings.azure_openai_endpoint, settings.azure_openai_api_key
        ),
        "computer_vision": check_service(
            settings.azure_vision_endpoint, settings.azure_vision_key
        ),
        "translator": check_service(
            settings.azure_translator_endpoint, settings.azure_translator_key
        ),
        "content_safety": check_service(
            settings.azure_content_safety_endpoint, settings.azure_content_safety_key
        ),
        "ai_search": check_service(
            settings.azure_search_endpoint, settings.azure_search_admin_key
        ),
    }

    all_configured = all(v == "configured" for v in services.values())

    return HealthResponse(
        status="healthy" if all_configured else "partially_configured",
        services=services,
    )


@app.get("/api/v1/info", tags=["Info"])
async def api_info():
    """Return API information and AI-102 coverage summary."""
    return {
        "name": "Azure AI Foundry Document Management",
        "version": "1.0.0",
        "ai102_coverage": {
            "document_intelligence": {
                "endpoint": "POST /api/v1/documents/analyze",
                "models": ["prebuilt-read", "prebuilt-layout", "prebuilt-invoice", "prebuilt-receipt", "prebuilt-idDocument"],
                "skills": ["Text extraction", "Table detection", "Key-value pairs", "Multi-language"],
            },
            "ai_language": {
                "endpoints": [
                    "POST /api/v1/analysis/nlp",
                    "POST /api/v1/analysis/sentiment",
                    "POST /api/v1/analysis/entities",
                    "POST /api/v1/analysis/pii",
                    "POST /api/v1/analysis/summarize",
                ],
                "skills": ["Language detection", "Sentiment + opinion mining", "NER", "Entity linking", "PII redaction", "Summarization"],
            },
            "azure_openai": {
                "endpoints": [
                    "POST /api/v1/analysis/qa",
                    "POST /api/v1/analysis/generate",
                    "POST /api/v1/analysis/classify",
                    "POST /api/v1/analysis/summarize-llm",
                ],
                "skills": ["RAG pattern", "Prompt engineering", "Multi-turn chat", "Document generation", "Zero-shot classification"],
            },
            "computer_vision": {
                "endpoints": [
                    "POST /api/v1/documents/ocr",
                    "POST /api/v1/documents/vision-analyze",
                ],
                "skills": ["OCR (printed + handwritten)", "Image captioning", "Object detection", "People detection", "Tags"],
            },
            "translator": {
                "endpoints": [
                    "POST /api/v1/analysis/translate",
                    "GET /api/v1/analysis/languages",
                ],
                "skills": ["Multi-target translation", "Language detection", "Transliteration", "Dictionary lookup"],
            },
            "content_safety": {
                "endpoints": [
                    "POST /api/v1/analysis/safety",
                    "POST /api/v1/analysis/safety/image",
                ],
                "skills": ["Text moderation", "Image moderation", "Severity levels (0-6)", "4 harm categories"],
            },
            "ai_search": {
                "endpoints": [
                    "POST /api/v1/search/query",
                    "POST /api/v1/search/index/document",
                    "POST /api/v1/search/index/create",
                ],
                "skills": ["Semantic search", "Vector search", "Faceted filtering", "Highlighting", "AI enrichment"],
            },
        },
    }

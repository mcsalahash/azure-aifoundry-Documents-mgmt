"""
Text & content analysis routes.
Covers NLP (Language), OpenAI, Translation, and Content Safety.
"""
import logging
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends, Body
from typing import Optional

from app.models.schemas import (
    LanguageAnalysisRequest,
    LanguageAnalysisResponse,
    DocumentQARequest,
    DocumentQAResponse,
    DocumentGenerationRequest,
    DocumentSummarizationRequest,
    TranslationRequest,
    TranslationResponse,
    ContentSafetyRequest,
    ContentSafetyResponse,
    SupportedLanguage,
)
from app.services.ai_language import AILanguageService
from app.services.openai_service import AzureOpenAIService
from app.services.translation_service import TranslationService
from app.services.content_safety import ContentSafetyService
from app.services.vision_service import VisionService
from app.utils.file_handler import read_upload_file, extract_text_from_pdf, extract_text_from_docx, is_image

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/analysis", tags=["Text Analysis & AI Language"])


def get_language_service() -> AILanguageService:
    try:
        return AILanguageService()
    except ValueError as e:
        raise HTTPException(status_code=503, detail=str(e))


def get_openai_service() -> AzureOpenAIService:
    try:
        return AzureOpenAIService()
    except ValueError as e:
        raise HTTPException(status_code=503, detail=str(e))


def get_translation_service() -> TranslationService:
    try:
        return TranslationService()
    except ValueError as e:
        raise HTTPException(status_code=503, detail=str(e))


def get_content_safety_service() -> ContentSafetyService:
    try:
        return ContentSafetyService()
    except ValueError as e:
        raise HTTPException(status_code=503, detail=str(e))


def get_vision_service() -> VisionService:
    try:
        return VisionService()
    except ValueError as e:
        raise HTTPException(status_code=503, detail=str(e))


# ── Azure AI Language ──────────────────────────────────────────────────────

@router.post(
    "/nlp",
    response_model=LanguageAnalysisResponse,
    summary="Full NLP analysis with Azure AI Language",
    description="""
    Perform comprehensive NLP analysis on text.

    **AI-102 Skills:**
    - Language detection (ISO codes + confidence)
    - Sentiment analysis with opinion mining
    - Key phrase extraction
    - Named Entity Recognition (Person, Location, Organization, etc.)
    - PII detection and redaction
    - Abstractive and extractive summarization
    """,
)
async def analyze_text(
    request: LanguageAnalysisRequest,
    service: AILanguageService = Depends(get_language_service),
):
    return await service.analyze_text(
        text=request.text,
        language=request.language,
        operations=request.operations,
    )


@router.post(
    "/sentiment",
    summary="Sentiment analysis with opinion mining",
    description="""
    Analyze document sentiment with opinion mining.

    **AI-102 Skills:** Opinion mining identifies sentiment targets and assessments.
    E.g., 'The delivery was fast but the packaging was poor' →
    delivery=positive, packaging=negative.
    """,
)
async def analyze_sentiment(
    text: str = Body(..., embed=True),
    language: str = Body(default="fr", embed=True),
    service: AILanguageService = Depends(get_language_service),
):
    result = await service.analyze_sentiment(text, language)
    return result


@router.post(
    "/entities",
    summary="Named Entity Recognition (NER)",
    description="""
    Identify and categorize named entities in text.

    **AI-102 Skills:** NER categories: Person, Location, Organization,
    DateTime, Quantity, URL, Email, Phone, IP address, etc.
    """,
)
async def recognize_entities(
    text: str = Body(..., embed=True),
    language: str = Body(default="fr", embed=True),
    service: AILanguageService = Depends(get_language_service),
):
    entities = await service.recognize_entities(text, language)
    linked = await service.recognize_linked_entities(text, language)
    return {"entities": entities, "linked_entities": linked}


@router.post(
    "/pii",
    summary="PII detection and redaction",
    description="""
    Detect and redact Personally Identifiable Information from text.

    **AI-102 Skills:** PII categories: Email, Phone, SSN, CreditCard,
    Person name, Organization, Address, MedicalRecord, etc.
    """,
)
async def detect_pii(
    text: str = Body(..., embed=True),
    language: str = Body(default="fr", embed=True),
    service: AILanguageService = Depends(get_language_service),
):
    return await service.detect_pii(text, language)


@router.post(
    "/summarize",
    summary="Text summarization (abstractive + extractive)",
    description="""
    Generate AI-powered summaries of text documents.

    **AI-102 Skills:**
    - Extractive: selects key sentences from the original text
    - Abstractive: generates new summary using AI language model
    """,
)
async def summarize_text(
    text: str = Body(..., embed=True),
    language: str = Body(default="fr", embed=True),
    service: AILanguageService = Depends(get_language_service),
):
    return await service.summarize_text(text, language)


# ── Azure OpenAI ─────────────────────────────────────────────────────────────

@router.post(
    "/qa",
    response_model=DocumentQAResponse,
    summary="Document Q&A with Azure OpenAI (RAG pattern)",
    description="""
    Ask questions about a document using Azure OpenAI.

    **AI-102 Skills:**
    - Retrieval-Augmented Generation (RAG)
    - Prompt engineering with system/user roles
    - Multi-turn conversation management
    - GPT-4o for document understanding
    """,
)
async def document_qa(
    request: DocumentQARequest,
    service: AzureOpenAIService = Depends(get_openai_service),
):
    return await service.answer_document_question(request)


@router.post(
    "/summarize-llm",
    summary="Document summarization with Azure OpenAI",
    description="""
    Generate LLM-powered document summaries with configurable length.

    **AI-102 Skills:** Prompt engineering for different summary styles.
    """,
)
async def summarize_with_openai(
    request: DocumentSummarizationRequest,
    service: AzureOpenAIService = Depends(get_openai_service),
):
    summary = await service.summarize_document(request)
    return {"summary": summary}


@router.post(
    "/generate",
    summary="Generate documents with Azure OpenAI",
    description="""
    Generate professional documents (contracts, reports, etc.) using AI.

    **AI-102 Skills:** Document generation with structured prompts.
    """,
)
async def generate_document(
    request: DocumentGenerationRequest,
    service: AzureOpenAIService = Depends(get_openai_service),
):
    document = await service.generate_document(request)
    return {"document": document, "document_type": request.document_type}


@router.post(
    "/classify",
    summary="Classify document type and domain",
    description="""
    Classify a document by type, domain, and topics using zero-shot AI classification.

    **AI-102 Skills:** Zero-shot classification with Azure OpenAI.
    """,
)
async def classify_document(
    text: str = Body(..., embed=True),
    service: AzureOpenAIService = Depends(get_openai_service),
):
    return await service.classify_document(text)


@router.post(
    "/analyze-file",
    summary="Full analysis pipeline on uploaded file",
    description="""
    Upload a document file and run the complete AI analysis pipeline:
    1. Extract text (Document Intelligence / Vision OCR)
    2. NLP analysis (sentiment, entities, key phrases)
    3. AI Classification
    4. Content Safety check
    5. Summarization
    """,
)
async def analyze_file_pipeline(
    file: UploadFile = File(...),
    run_nlp: bool = Form(default=True),
    run_classification: bool = Form(default=True),
    run_safety: bool = Form(default=True),
    run_summary: bool = Form(default=True),
    language_service: AILanguageService = Depends(get_language_service),
    openai_service: AzureOpenAIService = Depends(get_openai_service),
    safety_service: ContentSafetyService = Depends(get_content_safety_service),
    vision_service: VisionService = Depends(get_vision_service),
):
    content, extension = await read_upload_file(file)

    # Extract text based on file type
    extracted_text = ""
    if extension == "pdf":
        extracted_text = await extract_text_from_pdf(content)
    elif extension == "docx":
        extracted_text = await extract_text_from_docx(content)
    elif extension == "txt":
        extracted_text = content.decode("utf-8", errors="ignore")
    elif is_image(extension):
        ocr_result = await vision_service.extract_text_from_image(content)
        extracted_text = ocr_result.get("full_text", "")
    else:
        raise HTTPException(
            status_code=415,
            detail=f"Unsupported file type '{extension}'. Supported: PDF, DOCX, TXT, PNG, JPG, TIFF",
        )

    if not extracted_text:
        raise HTTPException(status_code=422, detail="Could not extract text from file")

    pipeline_result = {
        "filename": file.filename,
        "extracted_text_length": len(extracted_text),
        "extracted_text_preview": extracted_text[:500],
    }

    # NLP Analysis
    if run_nlp:
        nlp_result = await language_service.analyze_text(
            text=extracted_text[:5000],  # Token limit
            operations=["language_detection", "sentiment", "key_phrases", "entities"],
        )
        pipeline_result["nlp"] = {
            "detected_language": nlp_result.detected_language,
            "detected_language_code": nlp_result.detected_language_code,
            "sentiment": nlp_result.sentiment.sentiment if nlp_result.sentiment else None,
            "key_phrases": nlp_result.key_phrases[:10],
            "entities_count": len(nlp_result.entities),
            "top_entities": [
                {"text": e.text, "category": e.category}
                for e in nlp_result.entities[:10]
            ],
        }

    # Document Classification
    if run_classification:
        classification = await openai_service.classify_document(extracted_text)
        pipeline_result["classification"] = classification

    # Content Safety
    if run_safety:
        safety_result = await safety_service.analyze_text(
            ContentSafetyRequest(text=extracted_text[:1000])
        )
        pipeline_result["content_safety"] = {
            "is_safe": safety_result.is_safe,
            "blocked_reason": safety_result.blocked_reason,
            "categories": [
                {"category": c.category, "severity": c.severity}
                for c in safety_result.categories
            ],
        }

    # Summarization
    if run_summary:
        nlp_summary = await language_service.summarize_text(
            extracted_text[:5000],
            language=pipeline_result.get("nlp", {}).get("detected_language_code", "en"),
        )
        pipeline_result["summary"] = nlp_summary

    return pipeline_result


# ── Translation ───────────────────────────────────────────────────────────────

@router.post(
    "/translate",
    response_model=TranslationResponse,
    summary="Translate text with Azure AI Translator",
    description="""
    Translate text to one or multiple target languages simultaneously.

    **AI-102 Skills:**
    - Multi-language translation in one API call
    - Auto-detection of source language
    - Support for 100+ languages
    """,
)
async def translate_text(
    request: TranslationRequest,
    service: TranslationService = Depends(get_translation_service),
):
    return await service.translate(request)


@router.get(
    "/languages",
    summary="List supported translation languages",
)
async def list_languages(service: TranslationService = Depends(get_translation_service)):
    return await service.list_languages()


# ── Content Safety ───────────────────────────────────────────────────────────

@router.post(
    "/safety",
    response_model=ContentSafetyResponse,
    summary="Content safety check with Azure AI Content Safety",
    description="""
    Analyze text for harmful content across 4 categories.

    **AI-102 Skills:**
    - Categories: Hate, Violence, Sexual, Self-harm
    - Severity levels: 0 (safe), 2 (low), 4 (medium), 6 (high)
    - Configurable safety thresholds
    """,
)
async def check_content_safety(
    request: ContentSafetyRequest,
    service: ContentSafetyService = Depends(get_content_safety_service),
):
    return await service.analyze_text(request)


@router.post(
    "/safety/image",
    response_model=ContentSafetyResponse,
    summary="Image content safety check",
)
async def check_image_safety(
    file: UploadFile = File(...),
    service: ContentSafetyService = Depends(get_content_safety_service),
):
    content, extension = await read_upload_file(file)
    return await service.analyze_image(content)

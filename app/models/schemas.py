"""
Pydantic schemas for request/response models.
Covers all AI-102 service scenarios.
"""
from pydantic import BaseModel, Field
from typing import Optional, Any
from enum import Enum


# ── Enums ───────────────────────────────────────────────────────────────────

class DocumentModelType(str, Enum):
    """Document Intelligence pre-built models (AI-102)."""
    PREBUILT_READ = "prebuilt-read"
    PREBUILT_LAYOUT = "prebuilt-layout"
    PREBUILT_INVOICE = "prebuilt-invoice"
    PREBUILT_RECEIPT = "prebuilt-receipt"
    PREBUILT_ID_DOCUMENT = "prebuilt-idDocument"
    PREBUILT_BUSINESS_CARD = "prebuilt-businessCard"
    PREBUILT_TAX_US_W2 = "prebuilt-tax.us.w2"


class AnalysisFeature(str, Enum):
    """Azure AI Vision analysis features (AI-102)."""
    CAPTION = "Caption"
    DENSE_CAPTIONS = "DenseCaptions"
    OBJECTS = "Objects"
    PEOPLE = "People"
    READ = "Read"
    SMART_CROPS = "SmartCrops"
    TAGS = "Tags"


class SupportedLanguage(str, Enum):
    """Supported languages for translation."""
    FRENCH = "fr"
    ENGLISH = "en"
    SPANISH = "es"
    GERMAN = "de"
    ARABIC = "ar"
    CHINESE_SIMPLIFIED = "zh-Hans"
    PORTUGUESE = "pt"
    ITALIAN = "it"


# ── Document Intelligence Schemas ────────────────────────────────────────────

class DocumentAnalysisRequest(BaseModel):
    model_id: DocumentModelType = Field(
        default=DocumentModelType.PREBUILT_READ,
        description="Document Intelligence model to use",
    )
    url: Optional[str] = Field(
        default=None,
        description="URL of document to analyze (alternative to file upload)",
    )


class KeyValuePair(BaseModel):
    key: str
    value: Optional[str]
    confidence: Optional[float]


class DocumentTable(BaseModel):
    row_count: int
    column_count: int
    cells: list[dict[str, Any]]


class DocumentAnalysisResponse(BaseModel):
    model_id: str
    extracted_text: str
    pages: int
    key_value_pairs: list[KeyValuePair] = []
    tables: list[DocumentTable] = []
    languages: list[str] = []
    confidence: Optional[float] = None
    raw_result: Optional[dict[str, Any]] = None


# ── AI Language Schemas ──────────────────────────────────────────────────────

class LanguageAnalysisRequest(BaseModel):
    text: str = Field(description="Text to analyze")
    language: Optional[str] = Field(default=None, description="ISO 639-1 language code")
    operations: list[str] = Field(
        default=["language_detection", "sentiment", "key_phrases", "entities", "summary"],
        description="NLP operations to perform",
    )


class SentimentResult(BaseModel):
    sentiment: str
    confidence_scores: dict[str, float]
    sentences: list[dict[str, Any]] = []


class EntityResult(BaseModel):
    text: str
    category: str
    subcategory: Optional[str]
    confidence: float
    offset: int
    length: int


class PiiEntityResult(BaseModel):
    text: str
    category: str
    confidence: float
    redacted_text: str


class LanguageAnalysisResponse(BaseModel):
    detected_language: Optional[str] = None
    language_confidence: Optional[float] = None
    sentiment: Optional[SentimentResult] = None
    key_phrases: list[str] = []
    entities: list[EntityResult] = []
    linked_entities: list[dict[str, Any]] = []
    pii_entities: list[PiiEntityResult] = []
    pii_redacted_text: Optional[str] = None
    abstractive_summary: Optional[str] = None
    extractive_summary: Optional[str] = None


# ── Azure OpenAI Schemas ─────────────────────────────────────────────────────

class ChatMessage(BaseModel):
    role: str = Field(description="Message role: system, user, or assistant")
    content: str


class DocumentQARequest(BaseModel):
    question: str = Field(description="Question about the document")
    document_context: str = Field(description="Document content to query against")
    chat_history: list[ChatMessage] = Field(default=[], description="Conversation history")
    max_tokens: int = Field(default=1000, ge=100, le=4000)
    temperature: float = Field(default=0.3, ge=0.0, le=2.0)


class DocumentQAResponse(BaseModel):
    answer: str
    tokens_used: int
    model: str


class DocumentGenerationRequest(BaseModel):
    document_type: str = Field(description="Type of document to generate (e.g., 'contract', 'report', 'summary')")
    instructions: str = Field(description="Detailed instructions for document generation")
    language: str = Field(default="fr", description="Output language")
    max_tokens: int = Field(default=2000, ge=200, le=4000)


class DocumentSummarizationRequest(BaseModel):
    text: str = Field(description="Document content to summarize")
    summary_length: str = Field(default="medium", description="short | medium | long")
    language: str = Field(default="fr")


# ── Computer Vision Schemas ──────────────────────────────────────────────────

class VisionAnalysisRequest(BaseModel):
    features: list[AnalysisFeature] = Field(
        default=[AnalysisFeature.READ, AnalysisFeature.CAPTION, AnalysisFeature.TAGS],
        description="Vision features to extract",
    )
    url: Optional[str] = Field(default=None, description="Image URL to analyze")


class VisionAnalysisResponse(BaseModel):
    caption: Optional[str] = None
    caption_confidence: Optional[float] = None
    dense_captions: list[dict[str, Any]] = []
    tags: list[dict[str, Any]] = []
    objects: list[dict[str, Any]] = []
    people: list[dict[str, Any]] = []
    extracted_text: Optional[str] = None
    ocr_lines: list[str] = []
    smart_crops: list[dict[str, Any]] = []


# ── Translation Schemas ──────────────────────────────────────────────────────

class TranslationRequest(BaseModel):
    text: str = Field(description="Text to translate")
    target_languages: list[SupportedLanguage] = Field(
        default=[SupportedLanguage.FRENCH],
        description="Target languages for translation",
    )
    source_language: Optional[str] = Field(
        default=None, description="Source language (auto-detect if None)"
    )


class TranslationResult(BaseModel):
    target_language: str
    translated_text: str
    confidence: Optional[float] = None


class TranslationResponse(BaseModel):
    source_language: str
    source_language_confidence: float
    translations: list[TranslationResult]


# ── Content Safety Schemas ───────────────────────────────────────────────────

class ContentSafetyRequest(BaseModel):
    text: str = Field(description="Text content to moderate")
    output_type: str = Field(default="FourSeverityLevels", description="Output severity granularity")


class ContentSafetyCategory(BaseModel):
    category: str
    severity: int
    filtered: bool


class ContentSafetyResponse(BaseModel):
    is_safe: bool
    categories: list[ContentSafetyCategory]
    blocked_reason: Optional[str] = None


# ── Azure AI Search Schemas ──────────────────────────────────────────────────

class IndexDocumentRequest(BaseModel):
    document_id: str
    title: str
    content: str
    metadata: dict[str, Any] = {}
    language: str = "fr"


class SearchRequest(BaseModel):
    query: str = Field(description="Search query")
    top: int = Field(default=10, ge=1, le=50, description="Number of results")
    semantic_search: bool = Field(default=True, description="Use semantic / AI-powered search")
    filters: Optional[str] = Field(default=None, description="OData filter expression")
    highlight_fields: Optional[str] = Field(default=None, description="Fields to highlight")


class SearchResult(BaseModel):
    document_id: str
    title: str
    content_snippet: str
    score: float
    highlights: dict[str, list[str]] = {}
    metadata: dict[str, Any] = {}


class SearchResponse(BaseModel):
    total_count: int
    results: list[SearchResult]
    query: str


# ── Generic Response ─────────────────────────────────────────────────────────

class HealthResponse(BaseModel):
    status: str
    services: dict[str, str]
    version: str = "1.0.0"


class ErrorResponse(BaseModel):
    error: str
    detail: Optional[str] = None
    status_code: int

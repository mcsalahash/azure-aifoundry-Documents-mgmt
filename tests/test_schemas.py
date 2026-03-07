"""
Unit tests for Pydantic schemas.
No Azure credentials required.
"""
import pytest
from app.models.schemas import (
    DocumentAnalysisRequest,
    LanguageAnalysisRequest,
    DocumentQARequest,
    TranslationRequest,
    ContentSafetyRequest,
    SearchRequest,
    DocumentModelType,
    SupportedLanguage,
)


def test_document_analysis_request_defaults():
    req = DocumentAnalysisRequest()
    assert req.model_id == DocumentModelType.PREBUILT_READ
    assert req.url is None


def test_language_analysis_request_defaults():
    req = LanguageAnalysisRequest(text="Hello world")
    assert req.text == "Hello world"
    assert "sentiment" in req.operations
    assert "entities" in req.operations


def test_document_qa_request_validation():
    req = DocumentQARequest(
        question="What is the total amount?",
        document_context="The total amount is 1000 EUR.",
    )
    assert req.max_tokens == 1000
    assert req.temperature == 0.3
    assert req.chat_history == []


def test_translation_request_defaults():
    req = TranslationRequest(text="Bonjour")
    assert req.target_languages == [SupportedLanguage.FRENCH]
    assert req.source_language is None


def test_content_safety_request():
    req = ContentSafetyRequest(text="Safe content here")
    assert req.text == "Safe content here"
    assert req.output_type == "FourSeverityLevels"


def test_search_request_defaults():
    req = SearchRequest(query="azure ai")
    assert req.top == 10
    assert req.semantic_search is True
    assert req.filters is None


def test_document_model_type_values():
    assert DocumentModelType.PREBUILT_INVOICE == "prebuilt-invoice"
    assert DocumentModelType.PREBUILT_RECEIPT == "prebuilt-receipt"
    assert DocumentModelType.PREBUILT_ID_DOCUMENT == "prebuilt-idDocument"

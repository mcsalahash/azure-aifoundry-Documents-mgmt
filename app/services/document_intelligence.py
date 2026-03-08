"""
Azure AI Document Intelligence Service (AI-102)
================================================
Covers:
  - Prebuilt models: read, layout, invoice, receipt, ID document, business card
  - Custom model training concepts
  - Key-value pair extraction
  - Table extraction
  - Field extraction from structured documents
"""
import logging
from typing import Optional, Any
from azure.ai.documentintelligence import DocumentIntelligenceClient
from azure.ai.documentintelligence.models import AnalyzeDocumentRequest
from azure.core.credentials import AzureKeyCredential
from azure.core.exceptions import HttpResponseError

from app.config import get_settings
from app.models.schemas import (
    DocumentAnalysisResponse,
    KeyValuePair,
    DocumentTable,
    DocumentModelType,
)

logger = logging.getLogger(__name__)


class DocumentIntelligenceService:
    """
    Wraps Azure AI Document Intelligence SDK.

    AI-102 Skills covered:
    - Analyze documents with prebuilt models (read, layout, invoice, receipt, ID)
    - Extract key-value pairs and tables
    - Understand document structure (pages, lines, words)
    - Work with confidence scores
    """

    def __init__(self):
        settings = get_settings()
        if not settings.azure_document_intelligence_endpoint or not settings.azure_document_intelligence_key:
            raise ValueError(
                "Document Intelligence non configuré. "
                "Définissez AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT et AZURE_DOCUMENT_INTELLIGENCE_KEY dans .env"
            )
        self.client = DocumentIntelligenceClient(
            endpoint=settings.azure_document_intelligence_endpoint,
            credential=AzureKeyCredential(settings.azure_document_intelligence_key),
        )

    async def analyze_document_from_bytes(
        self,
        document_bytes: bytes,
        model_id: DocumentModelType = DocumentModelType.PREBUILT_READ,
        content_type: str = "application/pdf",
    ) -> DocumentAnalysisResponse:
        """
        Analyze a document from raw bytes using the specified prebuilt model.

        Args:
            document_bytes: Raw bytes of the document.
            model_id: Document Intelligence model to use.
            content_type: MIME type of the document.

        Returns:
            Structured analysis result.
        """
        try:
            poller = self.client.begin_analyze_document(
                model_id=model_id.value,
                analyze_request=document_bytes,
                content_type=content_type,
            )
            result = poller.result()
            return self._parse_result(result, model_id.value)

        except HttpResponseError as e:
            logger.error("Document Intelligence API error: %s", e.message)
            raise

    async def analyze_document_from_url(
        self,
        url: str,
        model_id: DocumentModelType = DocumentModelType.PREBUILT_READ,
    ) -> DocumentAnalysisResponse:
        """
        Analyze a document from a public URL.

        AI-102 concept: Document Intelligence can process documents from URLs
        without needing to download them locally first.
        """
        try:
            poller = self.client.begin_analyze_document(
                model_id=model_id.value,
                analyze_request=AnalyzeDocumentRequest(url_source=url),
            )
            result = poller.result()
            return self._parse_result(result, model_id.value)

        except HttpResponseError as e:
            logger.error("Document Intelligence API error: %s", e.message)
            raise

    def _parse_result(self, result: Any, model_id: str) -> DocumentAnalysisResponse:
        """
        Parse raw API result into our schema.

        AI-102 concept: Understanding the document analysis result structure:
        - pages[] → individual pages with lines, words
        - paragraphs[] → semantic paragraph blocks
        - tables[] → detected tables with cells
        - keyValuePairs[] → form fields (key=value)
        - documents[] → structured fields for prebuilt models
        """
        # Extract full text from all pages
        extracted_text = ""
        pages = 0
        if result.content:
            extracted_text = result.content
        if result.pages:
            pages = len(result.pages)

        # Extract key-value pairs (forms, invoices, etc.)
        key_value_pairs: list[KeyValuePair] = []
        if hasattr(result, "key_value_pairs") and result.key_value_pairs:
            for kv in result.key_value_pairs:
                key_text = kv.key.content if kv.key else ""
                value_text = kv.value.content if kv.value else None
                confidence = kv.confidence if hasattr(kv, "confidence") else None
                key_value_pairs.append(
                    KeyValuePair(key=key_text, value=value_text, confidence=confidence)
                )

        # Extract tables
        tables: list[DocumentTable] = []
        if hasattr(result, "tables") and result.tables:
            for table in result.tables:
                cells = []
                for cell in table.cells:
                    cells.append(
                        {
                            "row_index": cell.row_index,
                            "column_index": cell.column_index,
                            "content": cell.content,
                            "row_span": getattr(cell, "row_span", 1),
                            "column_span": getattr(cell, "column_span", 1),
                            "kind": getattr(cell, "kind", "content"),
                        }
                    )
                tables.append(
                    DocumentTable(
                        row_count=table.row_count,
                        column_count=table.column_count,
                        cells=cells,
                    )
                )

        # Detect languages
        languages = []
        if hasattr(result, "languages") and result.languages:
            languages = [lang.locale for lang in result.languages]

        # Handle structured fields for prebuilt models (invoice, receipt, etc.)
        structured_fields = {}
        if hasattr(result, "documents") and result.documents:
            for doc in result.documents:
                if doc.fields:
                    for field_name, field_value in doc.fields.items():
                        if field_value:
                            structured_fields[field_name] = {
                                "content": field_value.content,
                                "confidence": field_value.confidence,
                                "value": self._extract_field_value(field_value),
                            }
            # Merge structured fields into key_value_pairs for uniform response
            for field_name, field_data in structured_fields.items():
                key_value_pairs.append(
                    KeyValuePair(
                        key=field_name,
                        value=str(field_data.get("value", field_data.get("content", ""))),
                        confidence=field_data.get("confidence"),
                    )
                )

        return DocumentAnalysisResponse(
            model_id=model_id,
            extracted_text=extracted_text,
            pages=pages,
            key_value_pairs=key_value_pairs,
            tables=tables,
            languages=languages,
            raw_result={"structured_fields": structured_fields} if structured_fields else None,
        )

    def _extract_field_value(self, field: Any) -> Any:
        """Extract typed value from a document field."""
        if hasattr(field, "value_string") and field.value_string is not None:
            return field.value_string
        if hasattr(field, "value_number") and field.value_number is not None:
            return field.value_number
        if hasattr(field, "value_date") and field.value_date is not None:
            return str(field.value_date)
        if hasattr(field, "value_time") and field.value_time is not None:
            return str(field.value_time)
        if hasattr(field, "value_currency") and field.value_currency is not None:
            return field.value_currency.amount
        if hasattr(field, "value_address") and field.value_address is not None:
            addr = field.value_address
            return f"{getattr(addr, 'street_address', '')} {getattr(addr, 'city', '')} {getattr(addr, 'state', '')}".strip()
        return field.content if field.content else None

    def list_models(self) -> list[dict[str, str]]:
        """
        List all available Document Intelligence models.

        AI-102 concept: Understanding pre-built vs custom models.
        """
        return [
            {
                "model_id": m.value,
                "description": self._model_description(m),
            }
            for m in DocumentModelType
        ]

    def _model_description(self, model: DocumentModelType) -> str:
        descriptions = {
            DocumentModelType.PREBUILT_READ: "Extract text and structure from any document",
            DocumentModelType.PREBUILT_LAYOUT: "Extract text, tables, and structure with positions",
            DocumentModelType.PREBUILT_INVOICE: "Extract fields from invoices (vendor, amounts, line items)",
            DocumentModelType.PREBUILT_RECEIPT: "Extract fields from receipts (merchant, items, totals)",
            DocumentModelType.PREBUILT_ID_DOCUMENT: "Extract fields from IDs (name, DOB, expiry)",
            DocumentModelType.PREBUILT_BUSINESS_CARD: "Extract contact info from business cards",
            DocumentModelType.PREBUILT_TAX_US_W2: "Extract fields from US W2 tax forms",
        }
        return descriptions.get(model, "")

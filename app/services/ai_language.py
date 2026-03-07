"""
Azure AI Language Service (AI-102)
====================================
Covers:
  - Language detection
  - Sentiment analysis (opinion mining)
  - Key phrase extraction
  - Named Entity Recognition (NER)
  - Entity linking
  - PII detection and redaction
  - Text summarization (abstractive & extractive)
  - Custom text classification (concept)
"""
import logging
from typing import Optional
from azure.ai.textanalytics import TextAnalyticsClient
from azure.ai.textanalytics import (
    AbstractiveSummaryAction,
    ExtractiveSummaryAction,
    AnalyzeHealthcareEntitiesAction,
    RecognizePiiEntitiesAction,
    RecognizeEntitiesAction,
    ExtractKeyPhrasesAction,
    AnalyzeSentimentAction,
)
from azure.core.credentials import AzureKeyCredential
from azure.core.exceptions import HttpResponseError

from app.config import get_settings
from app.models.schemas import (
    LanguageAnalysisResponse,
    SentimentResult,
    EntityResult,
    PiiEntityResult,
)

logger = logging.getLogger(__name__)


class AILanguageService:
    """
    Wraps Azure AI Language (Text Analytics) SDK.

    AI-102 Skills covered:
    - Detect language (ISO codes, confidence)
    - Analyze sentiment with opinion mining
    - Extract key phrases
    - Named entity recognition (NER) with categories
    - Linked entity recognition
    - PII detection and text redaction
    - Abstractive and extractive summarization
    """

    def __init__(self):
        settings = get_settings()
        self.client = TextAnalyticsClient(
            endpoint=settings.azure_language_endpoint,
            credential=AzureKeyCredential(settings.azure_language_key),
        )

    async def analyze_text(
        self,
        text: str,
        language: Optional[str] = None,
        operations: Optional[list[str]] = None,
    ) -> LanguageAnalysisResponse:
        """
        Perform comprehensive NLP analysis on text.

        AI-102 concept: Text Analytics can run multiple operations in a
        single 'begin_analyze_actions' call to minimize API requests.

        Args:
            text: Input text.
            language: ISO 639-1 code. If None, auto-detected first.
            operations: List of NLP operations to perform.
        """
        if operations is None:
            operations = ["language_detection", "sentiment", "key_phrases", "entities", "summary"]

        response = LanguageAnalysisResponse()

        # Step 1: Language Detection (always done first if not provided)
        if "language_detection" in operations or language is None:
            lang_result = await self.detect_language(text)
            response.detected_language = lang_result["language"]
            response.language_confidence = lang_result["confidence"]
            if language is None:
                language = lang_result["iso6391_name"]

        # Step 2: Run remaining operations via batch actions
        actions = []
        if "sentiment" in operations:
            actions.append(AnalyzeSentimentAction(show_opinion_mining=True))
        if "key_phrases" in operations:
            actions.append(ExtractKeyPhrasesAction())
        if "entities" in operations:
            actions.append(RecognizeEntitiesAction())
        if "pii" in operations:
            actions.append(RecognizePiiEntitiesAction())
        if "summary" in operations:
            actions.append(AbstractiveSummaryAction(sentence_count=3))
            actions.append(ExtractiveSummaryAction(sentence_count=3))

        if actions:
            try:
                poller = self.client.begin_analyze_actions(
                    documents=[{"id": "1", "text": text, "language": language or "en"}],
                    actions=actions,
                )
                result = poller.result()

                action_idx = 0
                for page in result:
                    for i, action_result in enumerate(page):
                        action_type = type(actions[action_idx]).__name__

                        if not action_result.is_error:
                            if action_type == "AnalyzeSentimentAction":
                                response.sentiment = self._parse_sentiment(action_result)
                            elif action_type == "ExtractKeyPhrasesAction":
                                response.key_phrases = list(action_result.key_phrases)
                            elif action_type == "RecognizeEntitiesAction":
                                response.entities = self._parse_entities(action_result)
                            elif action_type == "RecognizePiiEntitiesAction":
                                response.pii_entities = self._parse_pii(action_result)
                                response.pii_redacted_text = action_result.redacted_text
                            elif action_type == "AbstractiveSummaryAction":
                                if action_result.summaries:
                                    response.abstractive_summary = " ".join(
                                        [s.text for s in action_result.summaries]
                                    )
                            elif action_type == "ExtractiveSummaryAction":
                                if action_result.sentences:
                                    response.extractive_summary = " ".join(
                                        [s.text for s in action_result.sentences]
                                    )
                        action_idx += 1

            except HttpResponseError as e:
                logger.error("AI Language API error: %s", e.message)
                raise

        return response

    async def detect_language(self, text: str) -> dict:
        """
        Detect the language of input text.

        AI-102 concept: Returns ISO 639-1 code, name, and confidence score.
        """
        results = self.client.detect_language(documents=[{"id": "1", "text": text}])
        result = results[0]
        if result.is_error:
            return {"language": "Unknown", "iso6391_name": "en", "confidence": 0.0}

        primary = result.primary_language
        return {
            "language": primary.name,
            "iso6391_name": primary.iso6391_name,
            "confidence": primary.confidence_score,
        }

    async def analyze_sentiment(self, text: str, language: str = "en") -> SentimentResult:
        """
        Analyze sentiment with opinion mining.

        AI-102 concept: Opinion mining identifies target-aspect pairs,
        e.g., 'the food was great' → target=food, sentiment=positive.
        """
        results = self.client.analyze_sentiment(
            documents=[{"id": "1", "text": text, "language": language}],
            show_opinion_mining=True,
        )
        result = results[0]
        if result.is_error:
            raise ValueError(f"Sentiment analysis error: {result.error}")

        sentences = []
        for sentence in result.sentences:
            sentence_data = {
                "text": sentence.text,
                "sentiment": sentence.sentiment,
                "confidence_scores": {
                    "positive": sentence.confidence_scores.positive,
                    "neutral": sentence.confidence_scores.neutral,
                    "negative": sentence.confidence_scores.negative,
                },
                "opinions": [],
            }
            for mined_opinion in sentence.mined_opinions:
                opinion_data = {
                    "target": mined_opinion.target.text,
                    "target_sentiment": mined_opinion.target.sentiment,
                    "assessments": [
                        {
                            "text": a.text,
                            "sentiment": a.sentiment,
                            "is_negated": a.is_negated,
                        }
                        for a in mined_opinion.assessments
                    ],
                }
                sentence_data["opinions"].append(opinion_data)
            sentences.append(sentence_data)

        return SentimentResult(
            sentiment=result.sentiment,
            confidence_scores={
                "positive": result.confidence_scores.positive,
                "neutral": result.confidence_scores.neutral,
                "negative": result.confidence_scores.negative,
            },
            sentences=sentences,
        )

    async def extract_key_phrases(self, text: str, language: str = "en") -> list[str]:
        """
        Extract key phrases from text.

        AI-102 concept: Key phrases identify the main points in text,
        useful for indexing and document classification.
        """
        results = self.client.extract_key_phrases(
            documents=[{"id": "1", "text": text, "language": language}]
        )
        result = results[0]
        if result.is_error:
            return []
        return list(result.key_phrases)

    async def recognize_entities(self, text: str, language: str = "en") -> list[EntityResult]:
        """
        Perform Named Entity Recognition (NER).

        AI-102 concept: NER identifies and categorizes entities such as
        Person, Organization, Location, DateTime, Quantity, etc.
        """
        results = self.client.recognize_entities(
            documents=[{"id": "1", "text": text, "language": language}]
        )
        result = results[0]
        if result.is_error:
            return []

        return [
            EntityResult(
                text=entity.text,
                category=entity.category,
                subcategory=entity.subcategory,
                confidence=entity.confidence_score,
                offset=entity.offset,
                length=entity.length,
            )
            for entity in result.entities
        ]

    async def recognize_linked_entities(self, text: str, language: str = "en") -> list[dict]:
        """
        Recognize linked entities (with Wikipedia/knowledge base links).

        AI-102 concept: Entity linking disambiguates entities and links them
        to a knowledge base (e.g., Wikipedia), providing richer context.
        """
        results = self.client.recognize_linked_entities(
            documents=[{"id": "1", "text": text, "language": language}]
        )
        result = results[0]
        if result.is_error:
            return []

        return [
            {
                "name": entity.name,
                "url": entity.url,
                "data_source": entity.data_source,
                "matches": [
                    {
                        "text": match.text,
                        "confidence": match.confidence_score,
                        "offset": match.offset,
                    }
                    for match in entity.matches
                ],
            }
            for entity in result.entities
        ]

    async def detect_pii(self, text: str, language: str = "en") -> dict:
        """
        Detect and redact Personally Identifiable Information (PII).

        AI-102 concept: PII detection identifies sensitive information such as
        email addresses, phone numbers, SSNs, credit card numbers, etc.
        The API returns both the entities found and a redacted version of the text.
        """
        results = self.client.recognize_pii_entities(
            documents=[{"id": "1", "text": text, "language": language}]
        )
        result = results[0]
        if result.is_error:
            return {"entities": [], "redacted_text": text}

        entities = [
            PiiEntityResult(
                text=entity.text,
                category=entity.category,
                confidence=entity.confidence_score,
                redacted_text="*" * len(entity.text),
            )
            for entity in result.entities
        ]
        return {"entities": entities, "redacted_text": result.redacted_text}

    async def summarize_text(self, text: str, language: str = "en") -> dict:
        """
        Generate abstractive and extractive summaries.

        AI-102 concept:
        - Extractive: selects key sentences from original text
        - Abstractive: generates new summary text (uses language model)
        """
        poller = self.client.begin_analyze_actions(
            documents=[{"id": "1", "text": text, "language": language}],
            actions=[
                AbstractiveSummaryAction(sentence_count=3),
                ExtractiveSummaryAction(sentence_count=3),
            ],
        )
        result = poller.result()

        abstractive_summary = ""
        extractive_summary = ""

        for page in result:
            for i, action_result in enumerate(page):
                if not action_result.is_error:
                    if i == 0 and hasattr(action_result, "summaries"):
                        abstractive_summary = " ".join(
                            [s.text for s in action_result.summaries]
                        )
                    elif i == 1 and hasattr(action_result, "sentences"):
                        extractive_summary = " ".join(
                            [s.text for s in action_result.sentences]
                        )

        return {
            "abstractive": abstractive_summary,
            "extractive": extractive_summary,
        }

    def _parse_sentiment(self, action_result) -> SentimentResult:
        doc = action_result.document_sentiment if hasattr(action_result, "document_sentiment") else None
        if doc is None and hasattr(action_result, "__iter__"):
            docs = list(action_result)
            doc = docs[0] if docs else None
        if doc is None:
            return SentimentResult(sentiment="unknown", confidence_scores={})
        return SentimentResult(
            sentiment=doc.sentiment,
            confidence_scores={
                "positive": doc.confidence_scores.positive,
                "neutral": doc.confidence_scores.neutral,
                "negative": doc.confidence_scores.negative,
            },
        )

    def _parse_entities(self, action_result) -> list[EntityResult]:
        entities = []
        for entity in action_result.entities:
            entities.append(
                EntityResult(
                    text=entity.text,
                    category=entity.category,
                    subcategory=entity.subcategory,
                    confidence=entity.confidence_score,
                    offset=entity.offset,
                    length=entity.length,
                )
            )
        return entities

    def _parse_pii(self, action_result) -> list[PiiEntityResult]:
        return [
            PiiEntityResult(
                text=entity.text,
                category=entity.category,
                confidence=entity.confidence_score,
                redacted_text="*" * len(entity.text),
            )
            for entity in action_result.entities
        ]

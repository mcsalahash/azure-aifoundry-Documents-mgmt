"""
Azure AI Translator Service (AI-102)
======================================
Covers:
  - Text translation (single and batch)
  - Language detection
  - Transliteration
  - Dictionary lookup
  - Supported languages listing
"""
import logging
import httpx
import uuid
from typing import Optional

from app.config import get_settings
from app.models.schemas import TranslationRequest, TranslationResponse, TranslationResult

logger = logging.getLogger(__name__)


class TranslationService:
    """
    Wraps Azure AI Translator REST API.

    AI-102 Skills covered:
    - Configure Translator service with key and region
    - Translate text to one or multiple languages simultaneously
    - Auto-detect source language
    - Transliterate text (change script without changing language)
    - Look up word definitions and alternatives
    - List supported translation languages
    """

    def __init__(self):
        settings = get_settings()
        if not settings.azure_translator_key:
            raise ValueError(
                "Azure Translator non configuré. "
                "Définissez AZURE_TRANSLATOR_KEY et AZURE_TRANSLATOR_REGION dans .env"
            )
        self.endpoint = settings.azure_translator_endpoint.rstrip("/")
        self.key = settings.azure_translator_key
        self.region = settings.azure_translator_region
        self.api_version = "3.0"

    def _get_headers(self) -> dict:
        """Build required headers for Translator API."""
        return {
            "Ocp-Apim-Subscription-Key": self.key,
            "Ocp-Apim-Subscription-Region": self.region,
            "Content-Type": "application/json",
            "X-ClientTraceId": str(uuid.uuid4()),
        }

    async def translate(self, request: TranslationRequest) -> TranslationResponse:
        """
        Translate text to one or more target languages.

        AI-102 concept: The Translator API can translate to multiple languages
        in a single API call, reducing costs and latency.

        Args:
            request: Contains text, target languages, and optional source language.

        Returns:
            Translation results with detected source language.
        """
        params = {
            "api-version": self.api_version,
            "to": [lang.value for lang in request.target_languages],
        }
        if request.source_language:
            params["from"] = request.source_language

        body = [{"text": request.text}]

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.endpoint}/translate",
                params=params,
                headers=self._get_headers(),
                json=body,
                timeout=30.0,
            )
            response.raise_for_status()
            data = response.json()

        result = data[0]
        detected_language = result.get("detectedLanguage", {})

        translations = []
        for t in result.get("translations", []):
            translations.append(
                TranslationResult(
                    target_language=t["to"],
                    translated_text=t["text"],
                )
            )

        return TranslationResponse(
            source_language=detected_language.get("language", request.source_language or "unknown"),
            source_language_confidence=detected_language.get("score", 1.0),
            translations=translations,
        )

    async def detect_language(self, text: str) -> dict:
        """
        Detect the language of a text.

        AI-102 concept: Language detection can return multiple possible languages
        with confidence scores and whether the result is ambiguous.

        Returns:
            Dictionary with language, confidence, and alternatives.
        """
        body = [{"text": text}]

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.endpoint}/detect",
                params={"api-version": self.api_version},
                headers=self._get_headers(),
                json=body,
                timeout=30.0,
            )
            response.raise_for_status()
            data = response.json()

        result = data[0]
        return {
            "language": result.get("language"),
            "confidence": result.get("score", 0.0),
            "is_translation_supported": result.get("isTranslationSupported", False),
            "is_transliteration_supported": result.get("isTransliterationSupported", False),
            "alternatives": result.get("alternatives", []),
        }

    async def transliterate(
        self, text: str, language: str, from_script: str, to_script: str
    ) -> str:
        """
        Transliterate text from one script to another.

        AI-102 concept: Transliteration changes the script (writing system)
        without changing the language. E.g., Arabic → Latin script.

        Args:
            text: Text to transliterate.
            language: Language code (e.g., 'ar', 'zh').
            from_script: Source script (e.g., 'Arab').
            to_script: Target script (e.g., 'Latn').
        """
        body = [{"text": text}]

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.endpoint}/transliterate",
                params={
                    "api-version": self.api_version,
                    "language": language,
                    "fromScript": from_script,
                    "toScript": to_script,
                },
                headers=self._get_headers(),
                json=body,
                timeout=30.0,
            )
            response.raise_for_status()
            data = response.json()

        return data[0].get("text", "")

    async def dictionary_lookup(
        self, word: str, from_language: str, to_language: str
    ) -> list[dict]:
        """
        Look up dictionary definitions and alternatives.

        AI-102 concept: Dictionary lookup provides bilingual dictionary
        entries with part-of-speech tags and back-translations.

        Returns:
            List of translation alternatives with confidence and examples.
        """
        body = [{"text": word}]

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.endpoint}/dictionary/lookup",
                params={
                    "api-version": self.api_version,
                    "from": from_language,
                    "to": to_language,
                },
                headers=self._get_headers(),
                json=body,
                timeout=30.0,
            )
            response.raise_for_status()
            data = response.json()

        result = data[0]
        return [
            {
                "normalized_target": t.get("normalizedTarget"),
                "display_target": t.get("displayTarget"),
                "pos_tag": t.get("posTag"),
                "confidence": t.get("confidence", 0.0),
                "back_translations": [
                    bt.get("displayText") for bt in t.get("backTranslations", [])
                ],
            }
            for t in result.get("translations", [])
        ]

    async def list_languages(self) -> dict:
        """
        List all supported languages for translation.

        AI-102 concept: Understanding which languages and scripts are
        supported by the Translator API.

        Returns:
            Dictionary with translation, transliteration, and dictionary languages.
        """
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.endpoint}/languages",
                params={"api-version": self.api_version},
                timeout=30.0,
            )
            response.raise_for_status()
            data = response.json()

        # Return simplified list of translation languages
        translation_langs = {
            code: {"name": info.get("name"), "nativeName": info.get("nativeName")}
            for code, info in data.get("translation", {}).items()
        }
        return {
            "translation_count": len(translation_langs),
            "languages": translation_langs,
        }

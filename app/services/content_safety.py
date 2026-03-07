"""
Azure AI Content Safety Service (AI-102)
==========================================
Covers:
  - Text content moderation (Hate, Violence, Sexual, Self-harm)
  - Image content moderation
  - Severity levels (0-6)
  - Blocklist management
  - Shield prompts (jailbreak detection)
"""
import logging
from azure.ai.contentsafety import ContentSafetyClient
from azure.ai.contentsafety.models import (
    AnalyzeTextOptions,
    TextCategory,
    AnalyzeImageOptions,
    ImageData,
)
from azure.core.credentials import AzureKeyCredential
from azure.core.exceptions import HttpResponseError

from app.config import get_settings
from app.models.schemas import (
    ContentSafetyRequest,
    ContentSafetyResponse,
    ContentSafetyCategory,
)

logger = logging.getLogger(__name__)

# Severity threshold: content with severity >= this value is considered unsafe
SAFETY_THRESHOLD = 2


class ContentSafetyService:
    """
    Wraps Azure AI Content Safety SDK.

    AI-102 Skills covered:
    - Analyze text for harmful content categories
    - Understand severity levels (0=safe, 2=low, 4=medium, 6=high)
    - Configure safety thresholds for different use cases
    - Analyze images for harmful content
    - Protect against prompt injection/jailbreak attempts
    """

    def __init__(self):
        settings = get_settings()
        self.client = ContentSafetyClient(
            endpoint=settings.azure_content_safety_endpoint,
            credential=AzureKeyCredential(settings.azure_content_safety_key),
        )

    async def analyze_text(self, request: ContentSafetyRequest) -> ContentSafetyResponse:
        """
        Analyze text content for safety across 4 harm categories.

        AI-102 concept: Content Safety API returns severity scores (0-6) for:
        - Hate: hate speech, discrimination
        - Violence: violent content
        - Sexual: adult/sexual content
        - SelfHarm: self-harm or suicide content

        Severity scale:
        - 0: Safe
        - 2: Low severity
        - 4: Medium severity
        - 6: High severity

        Args:
            request: Text content and output type configuration.

        Returns:
            Safety analysis with per-category severity scores.
        """
        try:
            options = AnalyzeTextOptions(
                text=request.text,
                categories=[
                    TextCategory.HATE,
                    TextCategory.VIOLENCE,
                    TextCategory.SEXUAL,
                    TextCategory.SELF_HARM,
                ],
                output_type=request.output_type,
            )
            response = self.client.analyze_text(options)

            categories = []
            is_safe = True
            blocked_reason = None

            category_results = {
                "Hate": response.categories_analysis[0] if response.categories_analysis else None,
                "Violence": response.categories_analysis[1] if len(response.categories_analysis) > 1 else None,
                "Sexual": response.categories_analysis[2] if len(response.categories_analysis) > 2 else None,
                "SelfHarm": response.categories_analysis[3] if len(response.categories_analysis) > 3 else None,
            }

            for cat_name, cat_result in category_results.items():
                if cat_result is None:
                    continue
                severity = cat_result.severity or 0
                filtered = severity >= SAFETY_THRESHOLD

                if filtered:
                    is_safe = False
                    blocked_reason = f"Content blocked due to {cat_name} (severity: {severity})"

                categories.append(
                    ContentSafetyCategory(
                        category=cat_name,
                        severity=severity,
                        filtered=filtered,
                    )
                )

            return ContentSafetyResponse(
                is_safe=is_safe,
                categories=categories,
                blocked_reason=blocked_reason if not is_safe else None,
            )

        except HttpResponseError as e:
            logger.error("Content Safety API error: %s", e.message)
            raise

    async def analyze_image(self, image_bytes: bytes) -> ContentSafetyResponse:
        """
        Analyze an image for harmful content.

        AI-102 concept: Image content moderation works similarly to text
        moderation, scanning for hate symbols, violent imagery, etc.

        Args:
            image_bytes: Raw image bytes to analyze.

        Returns:
            Safety analysis with per-category severity scores.
        """
        try:
            options = AnalyzeImageOptions(
                image=ImageData(content=image_bytes),
            )
            response = self.client.analyze_image(options)

            categories = []
            is_safe = True

            for cat_result in response.categories_analysis or []:
                severity = cat_result.severity or 0
                filtered = severity >= SAFETY_THRESHOLD
                if filtered:
                    is_safe = False

                categories.append(
                    ContentSafetyCategory(
                        category=str(cat_result.category),
                        severity=severity,
                        filtered=filtered,
                    )
                )

            return ContentSafetyResponse(
                is_safe=is_safe,
                categories=categories,
                blocked_reason="Image contains harmful content" if not is_safe else None,
            )

        except HttpResponseError as e:
            logger.error("Content Safety image analysis error: %s", e.message)
            raise

    async def detect_jailbreak(self, text: str) -> dict:
        """
        Detect prompt injection / jailbreak attempts.

        AI-102 concept: Jailbreak detection protects AI systems from
        adversarial prompts trying to bypass safety guardrails.

        Returns:
            Dictionary indicating if jailbreak attempt was detected.
        """
        try:
            from azure.ai.contentsafety.models import ShieldPromptOptions

            options = ShieldPromptOptions(
                user_prompt=text,
            )
            response = self.client.shield_prompt(options)

            return {
                "jailbreak_detected": response.user_prompt_analysis.attack_detected if response.user_prompt_analysis else False,
                "document_attacks": [
                    doc.attack_detected
                    for doc in (response.documents_analysis or [])
                ],
            }
        except Exception as e:
            logger.warning("Jailbreak detection unavailable: %s", str(e))
            return {"jailbreak_detected": False, "document_attacks": []}

    def get_severity_description(self, severity: int) -> str:
        """Human-readable description of severity levels."""
        descriptions = {
            0: "Safe - No harmful content detected",
            2: "Low - Mild content, generally acceptable",
            4: "Medium - Moderately harmful content",
            6: "High - Severely harmful content",
        }
        return descriptions.get(severity, f"Unknown severity: {severity}")

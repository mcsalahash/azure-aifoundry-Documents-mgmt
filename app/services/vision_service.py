"""
Azure AI Vision Service (AI-102)
==================================
Covers:
  - Image analysis (caption, tags, objects, people)
  - Optical Character Recognition (OCR) on images
  - Smart cropping / thumbnail generation
  - Dense captions
  - Background removal concept
"""
import logging
from typing import Optional
import requests

from azure.ai.vision.imageanalysis import ImageAnalysisClient
from azure.ai.vision.imageanalysis.models import VisualFeatures
from azure.core.credentials import AzureKeyCredential
from azure.core.exceptions import HttpResponseError

from app.config import get_settings
from app.models.schemas import VisionAnalysisRequest, VisionAnalysisResponse, AnalysisFeature

logger = logging.getLogger(__name__)

# Mapping from our enum to SDK VisualFeatures
FEATURE_MAP = {
    AnalysisFeature.CAPTION: VisualFeatures.CAPTION,
    AnalysisFeature.DENSE_CAPTIONS: VisualFeatures.DENSE_CAPTIONS,
    AnalysisFeature.OBJECTS: VisualFeatures.OBJECTS,
    AnalysisFeature.PEOPLE: VisualFeatures.PEOPLE,
    AnalysisFeature.READ: VisualFeatures.READ,
    AnalysisFeature.SMART_CROPS: VisualFeatures.SMART_CROPS,
    AnalysisFeature.TAGS: VisualFeatures.TAGS,
}


class VisionService:
    """
    Wraps Azure AI Vision (Image Analysis 4.0) SDK.

    AI-102 Skills covered:
    - Analyze images for captions, objects, people, tags
    - OCR: extract text from images (including handwriting)
    - Understand confidence scores for AI predictions
    - Configure visual features per use case
    - Process images from bytes or URLs
    """

    def __init__(self):
        settings = get_settings()
        if not settings.azure_vision_endpoint or not settings.azure_vision_key:
            raise ValueError(
                "Azure AI Vision non configuré. "
                "Définissez AZURE_VISION_ENDPOINT et AZURE_VISION_KEY dans .env"
            )
        self.client = ImageAnalysisClient(
            endpoint=settings.azure_vision_endpoint,
            credential=AzureKeyCredential(settings.azure_vision_key),
        )

    async def analyze_image_from_bytes(
        self,
        image_bytes: bytes,
        features: Optional[list[AnalysisFeature]] = None,
    ) -> VisionAnalysisResponse:
        """
        Analyze an image from raw bytes.

        AI-102 concept: Vision API processes images and returns structured
        results with confidence scores for each detected feature.

        Args:
            image_bytes: Raw image bytes.
            features: List of visual features to analyze.

        Returns:
            Structured vision analysis result.
        """
        if features is None:
            features = [AnalysisFeature.CAPTION, AnalysisFeature.READ, AnalysisFeature.TAGS]

        sdk_features = [FEATURE_MAP[f] for f in features if f in FEATURE_MAP]

        try:
            result = self.client.analyze(
                image_data=image_bytes,
                visual_features=sdk_features,
                gender_neutral_caption=True,
            )
            return self._parse_result(result)

        except HttpResponseError as e:
            logger.error("Azure AI Vision API error: %s", e.message)
            raise

    async def analyze_image_from_url(
        self,
        url: str,
        features: Optional[list[AnalysisFeature]] = None,
    ) -> VisionAnalysisResponse:
        """
        Analyze an image from a public URL.

        AI-102 concept: Vision API can analyze images directly from URLs,
        useful for analyzing images stored in Azure Blob Storage.
        """
        if features is None:
            features = [AnalysisFeature.CAPTION, AnalysisFeature.READ, AnalysisFeature.TAGS]

        sdk_features = [FEATURE_MAP[f] for f in features if f in FEATURE_MAP]

        try:
            result = self.client.analyze_from_url(
                image_url=url,
                visual_features=sdk_features,
                gender_neutral_caption=True,
            )
            return self._parse_result(result)

        except HttpResponseError as e:
            logger.error("Azure AI Vision API error: %s", e.message)
            raise

    async def extract_text_from_image(self, image_bytes: bytes) -> dict:
        """
        Perform OCR on an image to extract text.

        AI-102 concept: Computer Vision OCR can extract text from images,
        scanned documents, signs, etc. Supports both printed and handwritten text.
        Returns text organized by pages, blocks, lines, and words.

        Returns:
            Dictionary with full text and structured OCR results.
        """
        try:
            result = self.client.analyze(
                image_data=image_bytes,
                visual_features=[VisualFeatures.READ],
            )

            if not result.read:
                return {"full_text": "", "lines": [], "words": []}

            full_text = ""
            lines = []
            all_words = []

            for block in result.read.blocks:
                for line in block.lines:
                    full_text += line.text + "\n"
                    line_data = {
                        "text": line.text,
                        "bounding_polygon": [
                            {"x": p.x, "y": p.y}
                            for p in (line.bounding_polygon or [])
                        ],
                        "words": [],
                    }
                    for word in line.words:
                        word_data = {
                            "text": word.text,
                            "confidence": word.confidence,
                            "bounding_polygon": [
                                {"x": p.x, "y": p.y}
                                for p in (word.bounding_polygon or [])
                            ],
                        }
                        line_data["words"].append(word_data)
                        all_words.append(word_data)
                    lines.append(line_data)

            return {
                "full_text": full_text.strip(),
                "lines": lines,
                "words": all_words,
            }

        except HttpResponseError as e:
            logger.error("OCR error: %s", e.message)
            raise

    def _parse_result(self, result) -> VisionAnalysisResponse:
        """Parse Vision API result into our response schema."""
        response = VisionAnalysisResponse()

        # Caption
        if result.caption:
            response.caption = result.caption.text
            response.caption_confidence = result.caption.confidence

        # Dense captions
        if result.dense_captions:
            response.dense_captions = [
                {
                    "text": dc.text,
                    "confidence": dc.confidence,
                    "bounding_box": {
                        "x": dc.bounding_box.x,
                        "y": dc.bounding_box.y,
                        "width": dc.bounding_box.width,
                        "height": dc.bounding_box.height,
                    } if dc.bounding_box else None,
                }
                for dc in result.dense_captions.list
            ]

        # Tags
        if result.tags:
            response.tags = [
                {"name": tag.name, "confidence": tag.confidence}
                for tag in result.tags.list
            ]

        # Objects
        if result.objects:
            response.objects = [
                {
                    "name": obj.tags[0].name if obj.tags else "unknown",
                    "confidence": obj.tags[0].confidence if obj.tags else 0.0,
                    "bounding_box": {
                        "x": obj.bounding_box.x,
                        "y": obj.bounding_box.y,
                        "width": obj.bounding_box.width,
                        "height": obj.bounding_box.height,
                    } if obj.bounding_box else None,
                }
                for obj in result.objects.list
            ]

        # People
        if result.people:
            response.people = [
                {
                    "confidence": person.confidence,
                    "bounding_box": {
                        "x": person.bounding_box.x,
                        "y": person.bounding_box.y,
                        "width": person.bounding_box.width,
                        "height": person.bounding_box.height,
                    } if person.bounding_box else None,
                }
                for person in result.people.list
            ]

        # OCR / Read
        if result.read:
            lines = []
            full_text = ""
            for block in result.read.blocks:
                for line in block.lines:
                    lines.append(line.text)
                    full_text += line.text + "\n"
            response.ocr_lines = lines
            response.extracted_text = full_text.strip()

        # Smart crops
        if result.smart_crops:
            response.smart_crops = [
                {
                    "aspect_ratio": crop.aspect_ratio,
                    "bounding_box": {
                        "x": crop.bounding_box.x,
                        "y": crop.bounding_box.y,
                        "width": crop.bounding_box.width,
                        "height": crop.bounding_box.height,
                    } if crop.bounding_box else None,
                }
                for crop in result.smart_crops.list
            ]

        return response

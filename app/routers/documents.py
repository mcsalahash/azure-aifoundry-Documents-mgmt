"""
Document management routes.
Handles upload, analysis with Document Intelligence, and Vision OCR.
"""
import logging
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends, Query
from fastapi.responses import JSONResponse
from typing import Optional
from azure.core.exceptions import HttpResponseError

from app.models.schemas import (
    DocumentAnalysisRequest,
    DocumentAnalysisResponse,
    VisionAnalysisRequest,
    VisionAnalysisResponse,
    DocumentModelType,
    AnalysisFeature,
)
from app.services.document_intelligence import DocumentIntelligenceService
from app.services.vision_service import VisionService
from app.utils.file_handler import read_upload_file, get_mime_type, is_image

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/documents", tags=["Documents & Document Intelligence"])


def get_doc_service() -> DocumentIntelligenceService:
    try:
        return DocumentIntelligenceService()
    except ValueError as e:
        raise HTTPException(status_code=503, detail=str(e))


def get_vision_service() -> VisionService:
    try:
        return VisionService()
    except ValueError as e:
        raise HTTPException(status_code=503, detail=str(e))


@router.post(
    "/analyze",
    response_model=DocumentAnalysisResponse,
    summary="Analyze document with Azure AI Document Intelligence",
    description="""
    Upload a document (PDF, DOCX, image) and analyze it using Azure AI Document Intelligence.

    **AI-102 Skills:**
    - Prebuilt models: read, layout, invoice, receipt, ID document, business card
    - Key-value pair extraction from forms
    - Table structure detection
    - Multi-language document support
    """,
)
async def analyze_document(
    file: UploadFile = File(..., description="Document file to analyze"),
    model_id: DocumentModelType = Form(
        default=DocumentModelType.PREBUILT_READ,
        description="Document Intelligence model to use",
    ),
    service: DocumentIntelligenceService = Depends(get_doc_service),
):
    content, extension = await read_upload_file(file)
    mime_type = get_mime_type(extension)

    result = await service.analyze_document_from_bytes(
        document_bytes=content,
        model_id=model_id,
        content_type=mime_type,
    )
    return result


@router.post(
    "/analyze-url",
    response_model=DocumentAnalysisResponse,
    summary="Analyze document from URL",
    description="Analyze a publicly accessible document using its URL.",
)
async def analyze_document_from_url(
    url: str = Form(..., description="Public URL of the document"),
    model_id: DocumentModelType = Form(default=DocumentModelType.PREBUILT_READ),
    service: DocumentIntelligenceService = Depends(get_doc_service),
):
    result = await service.analyze_document_from_url(url=url, model_id=model_id)
    return result


@router.get(
    "/models",
    summary="List available Document Intelligence models",
    description="""
    Returns all available Document Intelligence prebuilt models with descriptions.

    **AI-102 Skills:** Understanding prebuilt vs custom models.
    """,
)
async def list_models(service: DocumentIntelligenceService = Depends(get_doc_service)):
    return {"models": service.list_models()}


@router.post(
    "/ocr",
    response_model=VisionAnalysisResponse,
    summary="Extract text from image (OCR)",
    description="""
    Upload an image and extract text using Azure AI Vision OCR.

    **AI-102 Skills:**
    - Computer Vision Read API for text extraction
    - Supports printed and handwritten text
    - Returns text with bounding polygons
    """,
)
async def extract_text_from_image(
    file: UploadFile = File(..., description="Image file for OCR"),
    service: VisionService = Depends(get_vision_service),
):
    content, extension = await read_upload_file(file)

    if not is_image(extension):
        raise HTTPException(
            status_code=400,
            detail=f"File must be an image. Received: {extension}",
        )

    try:
        ocr_result = await service.extract_text_from_image(content)
    except HttpResponseError as e:
        raise HTTPException(status_code=e.status_code or 502, detail=str(e.message))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    return VisionAnalysisResponse(
        extracted_text=ocr_result["full_text"],
        ocr_lines=ocr_result["lines"],
    )


@router.post(
    "/vision-analyze",
    response_model=VisionAnalysisResponse,
    summary="Analyze image with Azure AI Vision",
    description="""
    Upload an image and analyze it for captions, objects, people, and tags.

    **AI-102 Skills:**
    - Image Analysis 4.0 API
    - Visual features: caption, dense captions, objects, people, tags, smart crops
    - Confidence scores for all detections
    """,
)
async def analyze_image(
    file: UploadFile = File(..., description="Image file to analyze"),
    features: str = Form(
        default="Caption,Read,Tags",
        description="Comma-separated list of features: Caption, DenseCaptions, Objects, People, Read, SmartCrops, Tags",
    ),
    service: VisionService = Depends(get_vision_service),
):
    content, extension = await read_upload_file(file)

    if not is_image(extension):
        raise HTTPException(
            status_code=400,
            detail=f"File must be an image. Received: {extension}",
        )

    feature_list = []
    for f in features.split(","):
        f = f.strip()
        try:
            feature_list.append(AnalysisFeature(f))
        except ValueError:
            logger.warning("Unknown feature: %s", f)

    result = await service.analyze_image_from_bytes(content, features=feature_list)
    return result

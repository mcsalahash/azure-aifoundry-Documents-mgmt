"""
File handling utilities.
Validates, reads, and converts uploaded documents.
"""
import io
import logging
from pathlib import Path
from fastapi import UploadFile, HTTPException, status

from app.config import get_settings

logger = logging.getLogger(__name__)

# MIME type → extension mapping
MIME_TYPE_MAP = {
    "application/pdf": "pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "docx",
    "text/plain": "txt",
    "image/png": "png",
    "image/jpeg": "jpg",
    "image/tiff": "tiff",
    "image/webp": "webp",
}

IMAGE_TYPES = {"png", "jpg", "jpeg", "tiff", "webp", "bmp"}
DOCUMENT_TYPES = {"pdf", "docx", "txt"}


async def read_upload_file(upload_file: UploadFile) -> tuple[bytes, str]:
    """
    Read and validate an uploaded file.

    Returns:
        Tuple of (file bytes, file extension).

    Raises:
        HTTPException: If file is too large or type not allowed.
    """
    settings = get_settings()

    # Read file bytes
    content = await upload_file.read()

    # Validate size
    if len(content) > settings.max_upload_size_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File too large. Maximum size: {settings.max_upload_size_mb}MB",
        )

    # Determine extension
    extension = ""
    if upload_file.filename:
        extension = Path(upload_file.filename).suffix.lstrip(".").lower()
    if not extension and upload_file.content_type:
        extension = MIME_TYPE_MAP.get(upload_file.content_type, "")

    # Validate extension
    if extension not in settings.allowed_extensions_list:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"File type '{extension}' not allowed. Allowed: {settings.allowed_extensions}",
        )

    return content, extension


def get_mime_type(extension: str) -> str:
    """Get MIME type from file extension."""
    reverse_map = {v: k for k, v in MIME_TYPE_MAP.items()}
    reverse_map["jpeg"] = "image/jpeg"
    return reverse_map.get(extension.lower(), "application/octet-stream")


def is_image(extension: str) -> bool:
    """Check if extension is an image type."""
    return extension.lower() in IMAGE_TYPES


def is_document(extension: str) -> bool:
    """Check if extension is a document type."""
    return extension.lower() in DOCUMENT_TYPES


async def extract_text_from_docx(content: bytes) -> str:
    """Extract plain text from DOCX bytes."""
    try:
        import docx
        doc = docx.Document(io.BytesIO(content))
        return "\n".join([para.text for para in doc.paragraphs if para.text.strip()])
    except Exception as e:
        logger.warning("DOCX text extraction failed: %s", str(e))
        return ""


async def extract_text_from_pdf(content: bytes) -> str:
    """Extract plain text from PDF bytes using PyMuPDF."""
    try:
        import fitz  # PyMuPDF
        doc = fitz.open(stream=content, filetype="pdf")
        text = ""
        for page in doc:
            text += page.get_text() + "\n"
        doc.close()
        return text.strip()
    except Exception as e:
        logger.warning("PDF text extraction failed: %s", str(e))
        return ""

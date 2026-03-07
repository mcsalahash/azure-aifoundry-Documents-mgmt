"""
Azure AI Search routes.
Handles document indexing and intelligent search.
"""
import logging
from fastapi import APIRouter, Depends, HTTPException, Body

from app.models.schemas import (
    SearchRequest,
    SearchResponse,
    IndexDocumentRequest,
)
from app.services.search_service import SearchService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/search", tags=["Azure AI Search"])


def get_search_service() -> SearchService:
    return SearchService()


@router.post(
    "/index/create",
    summary="Create or update search index",
    description="""
    Create the Azure AI Search index with semantic and vector search support.

    **AI-102 Skills:**
    - Design search indexes with field types
    - Configure semantic search (neural re-ranking)
    - Enable vector search for embedding-based similarity
    """,
)
async def create_index(service: SearchService = Depends(get_search_service)):
    return service.create_index()


@router.post(
    "/index/document",
    summary="Index a document for search",
    description="""
    Add a document to the Azure AI Search index.

    **AI-102 Skills:**
    - Document structure for search indexing
    - Rich metadata for filtering and faceting
    """,
)
async def index_document(
    request: IndexDocumentRequest,
    service: SearchService = Depends(get_search_service),
):
    return await service.index_document(request)


@router.post(
    "/query",
    response_model=SearchResponse,
    summary="Search documents with AI-powered ranking",
    description="""
    Search indexed documents using full-text or semantic search.

    **AI-102 Skills:**
    - Full-text search with BM25 ranking
    - Semantic search with Microsoft's neural re-ranker
    - Search result highlighting
    - OData filter expressions
    - Semantic captions and answers
    """,
)
async def search_documents(
    request: SearchRequest,
    service: SearchService = Depends(get_search_service),
):
    return await service.search(request)


@router.delete(
    "/index/document/{document_id}",
    summary="Delete a document from the index",
)
async def delete_document(
    document_id: str,
    service: SearchService = Depends(get_search_service),
):
    return await service.delete_document(document_id)


@router.get(
    "/index/stats",
    summary="Get index statistics",
    description="Returns document count and storage size for the search index.",
)
async def get_index_stats(service: SearchService = Depends(get_search_service)):
    return service.get_index_stats()

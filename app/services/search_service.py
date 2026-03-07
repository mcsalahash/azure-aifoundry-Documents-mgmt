"""
Azure AI Search Service (AI-102)
==================================
Covers:
  - Creating and managing search indexes
  - Indexing documents with rich metadata
  - Full-text search with highlighting
  - Semantic / AI-powered search (semantic ranker)
  - Vector search with embeddings
  - Faceted search and filters
  - Skillsets (AI enrichment pipeline)
"""
import logging
from typing import Optional, Any
from azure.search.documents import SearchClient
from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.indexes.models import (
    SearchIndex,
    SearchField,
    SearchFieldDataType,
    SimpleField,
    SearchableField,
    ComplexField,
    SemanticConfiguration,
    SemanticPrioritizedFields,
    SemanticField,
    SemanticSearch,
    VectorSearch,
    HnswAlgorithmConfiguration,
    VectorSearchProfile,
)
from azure.search.documents.models import VectorizedQuery, QueryType, QueryCaptionType, QueryAnswerType
from azure.core.credentials import AzureKeyCredential
from azure.core.exceptions import HttpResponseError

from app.config import get_settings
from app.models.schemas import (
    SearchRequest,
    SearchResponse,
    SearchResult,
    IndexDocumentRequest,
)

logger = logging.getLogger(__name__)

INDEX_SCHEMA_VERSION = "1"


class SearchService:
    """
    Wraps Azure AI Search SDK.

    AI-102 Skills covered:
    - Design and create search indexes with field types
    - Index documents with metadata and content
    - Execute full-text and semantic search queries
    - Configure semantic ranker for relevance
    - Use vector search for semantic similarity
    - Apply filters and facets for drill-down search
    - Understand AI enrichment skillsets
    """

    def __init__(self):
        settings = get_settings()
        self.credential = AzureKeyCredential(settings.azure_search_admin_key)
        self.endpoint = settings.azure_search_endpoint
        self.index_name = settings.azure_search_index_name

        self.index_client = SearchIndexClient(
            endpoint=self.endpoint,
            credential=self.credential,
        )
        self.search_client = SearchClient(
            endpoint=self.endpoint,
            index_name=self.index_name,
            credential=self.credential,
        )

    def create_index(self) -> dict:
        """
        Create the document search index with semantic and vector search support.

        AI-102 concept: Index design with:
        - Searchable fields (full-text search)
        - Filterable fields (facets, exact match)
        - Semantic configuration (cross-field ranking)
        - Vector fields (embedding-based similarity)

        Returns:
            Index creation result.
        """
        fields = [
            SimpleField(name="id", type=SearchFieldDataType.String, key=True),
            SearchableField(name="title", type=SearchFieldDataType.String, analyzer_name="fr.lucene"),
            SearchableField(name="content", type=SearchFieldDataType.String, analyzer_name="fr.lucene"),
            SimpleField(name="language", type=SearchFieldDataType.String, filterable=True, facetable=True),
            SimpleField(name="document_type", type=SearchFieldDataType.String, filterable=True, facetable=True),
            SimpleField(name="domain", type=SearchFieldDataType.String, filterable=True, facetable=True),
            SimpleField(name="upload_date", type=SearchFieldDataType.DateTimeOffset, filterable=True, sortable=True),
            SimpleField(name="file_size", type=SearchFieldDataType.Int64, filterable=True, sortable=True),
            SimpleField(name="page_count", type=SearchFieldDataType.Int32, filterable=True),
            SimpleField(name="tags", type=SearchFieldDataType.Collection(SearchFieldDataType.String), filterable=True, facetable=True),
            SearchField(
                name="content_vector",
                type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
                searchable=True,
                vector_search_dimensions=1536,  # text-embedding-ada-002 dimensions
                vector_search_profile_name="hnsw-profile",
            ),
        ]

        # Semantic configuration for AI-powered relevance ranking
        semantic_config = SemanticConfiguration(
            name="document-semantic-config",
            prioritized_fields=SemanticPrioritizedFields(
                title_field=SemanticField(field_name="title"),
                content_fields=[SemanticField(field_name="content")],
                keywords_fields=[SemanticField(field_name="tags")],
            ),
        )

        # Vector search configuration (HNSW algorithm)
        vector_search = VectorSearch(
            algorithms=[HnswAlgorithmConfiguration(name="hnsw-algorithm")],
            profiles=[
                VectorSearchProfile(
                    name="hnsw-profile",
                    algorithm_configuration_name="hnsw-algorithm",
                )
            ],
        )

        index = SearchIndex(
            name=self.index_name,
            fields=fields,
            semantic_search=SemanticSearch(configurations=[semantic_config]),
            vector_search=vector_search,
        )

        try:
            result = self.index_client.create_or_update_index(index)
            return {"status": "created", "index_name": result.name}
        except HttpResponseError as e:
            logger.error("Failed to create index: %s", e.message)
            raise

    async def index_document(self, request: IndexDocumentRequest) -> dict:
        """
        Index a document for search.

        AI-102 concept: Documents are indexed as JSON objects. Fields must
        match the index schema. The 'id' field is the unique key.

        Args:
            request: Document data to index.

        Returns:
            Indexing result with success/failure status.
        """
        from datetime import datetime, timezone

        document = {
            "id": request.document_id,
            "title": request.title,
            "content": request.content,
            "language": request.language,
            "upload_date": datetime.now(timezone.utc).isoformat(),
            "tags": request.metadata.get("tags", []),
            "document_type": request.metadata.get("document_type", "unknown"),
            "domain": request.metadata.get("domain", "unknown"),
            "file_size": request.metadata.get("file_size", 0),
            "page_count": request.metadata.get("page_count", 1),
        }

        try:
            result = self.search_client.upload_documents(documents=[document])
            return {
                "succeeded": result[0].succeeded,
                "key": result[0].key,
                "status_code": result[0].status_code,
            }
        except HttpResponseError as e:
            logger.error("Document indexing error: %s", e.message)
            raise

    async def search(self, request: SearchRequest) -> SearchResponse:
        """
        Search documents using full-text, semantic, or vector search.

        AI-102 concept:
        - Full-text search uses BM25 ranking
        - Semantic search uses Microsoft's neural re-ranker for better relevance
        - Both can be combined with filters (OData syntax)

        Args:
            request: Search query, top-k, semantic flag, and filters.

        Returns:
            Ranked search results with highlights and scores.
        """
        search_params: dict[str, Any] = {
            "search_text": request.query,
            "top": request.top,
            "include_total_count": True,
            "highlight_fields": request.highlight_fields or "content,title",
            "highlight_pre_tag": "<mark>",
            "highlight_post_tag": "</mark>",
        }

        if request.filters:
            search_params["filter"] = request.filters

        # AI-102: Semantic search with captions and answers
        if request.semantic_search:
            search_params["query_type"] = QueryType.SEMANTIC
            search_params["semantic_configuration_name"] = "document-semantic-config"
            search_params["query_caption"] = QueryCaptionType.EXTRACTIVE
            search_params["query_answer"] = QueryAnswerType.EXTRACTIVE

        try:
            results = self.search_client.search(**search_params)

            search_results = []
            for result in results:
                highlights = {}
                if result.get("@search.highlights"):
                    highlights = result["@search.highlights"]

                search_results.append(
                    SearchResult(
                        document_id=result.get("id", ""),
                        title=result.get("title", ""),
                        content_snippet=result.get("content", "")[:300],
                        score=result.get("@search.score", 0.0),
                        highlights=highlights,
                        metadata={
                            "language": result.get("language"),
                            "document_type": result.get("document_type"),
                            "domain": result.get("domain"),
                            "upload_date": str(result.get("upload_date", "")),
                            "tags": result.get("tags", []),
                        },
                    )
                )

            return SearchResponse(
                total_count=results.get_count() or len(search_results),
                results=search_results,
                query=request.query,
            )

        except HttpResponseError as e:
            logger.error("Search error: %s", e.message)
            raise

    async def delete_document(self, document_id: str) -> dict:
        """
        Delete a document from the search index.

        AI-102 concept: Documents can be deleted by key value.

        Returns:
            Deletion result.
        """
        try:
            result = self.search_client.delete_documents(
                documents=[{"id": document_id}]
            )
            return {"succeeded": result[0].succeeded, "key": document_id}
        except HttpResponseError as e:
            logger.error("Document deletion error: %s", e.message)
            raise

    def get_index_stats(self) -> dict:
        """
        Get index statistics (document count, storage size).

        AI-102 concept: Monitoring index health and capacity.

        Returns:
            Index statistics.
        """
        try:
            stats = self.index_client.get_index_statistics(self.index_name)
            return {
                "document_count": stats.document_count,
                "storage_size_bytes": stats.storage_size,
            }
        except HttpResponseError as e:
            logger.error("Failed to get index stats: %s", e.message)
            return {"document_count": 0, "storage_size_bytes": 0}

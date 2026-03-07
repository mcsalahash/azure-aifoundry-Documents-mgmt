"""
Application configuration using Pydantic Settings.
Loads environment variables from .env file.
"""
from pydantic_settings import BaseSettings
from pydantic import Field
from functools import lru_cache


class Settings(BaseSettings):
    # --- Azure Subscription ---
    azure_subscription_id: str = Field(default="", alias="AZURE_SUBSCRIPTION_ID")
    azure_resource_group: str = Field(default="", alias="AZURE_RESOURCE_GROUP")
    azure_location: str = Field(default="eastus", alias="AZURE_LOCATION")

    # --- Azure Document Intelligence ---
    azure_document_intelligence_endpoint: str = Field(
        default="", alias="AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT"
    )
    azure_document_intelligence_key: str = Field(
        default="", alias="AZURE_DOCUMENT_INTELLIGENCE_KEY"
    )

    # --- Azure AI Language ---
    azure_language_endpoint: str = Field(default="", alias="AZURE_LANGUAGE_ENDPOINT")
    azure_language_key: str = Field(default="", alias="AZURE_LANGUAGE_KEY")

    # --- Azure OpenAI ---
    azure_openai_endpoint: str = Field(default="", alias="AZURE_OPENAI_ENDPOINT")
    azure_openai_api_key: str = Field(default="", alias="AZURE_OPENAI_API_KEY")
    azure_openai_api_version: str = Field(
        default="2024-02-15-preview", alias="AZURE_OPENAI_API_VERSION"
    )
    azure_openai_chat_deployment: str = Field(
        default="gpt-4o", alias="AZURE_OPENAI_CHAT_DEPLOYMENT"
    )
    azure_openai_embedding_deployment: str = Field(
        default="text-embedding-ada-002", alias="AZURE_OPENAI_EMBEDDING_DEPLOYMENT"
    )

    # --- Azure AI Vision ---
    azure_vision_endpoint: str = Field(default="", alias="AZURE_VISION_ENDPOINT")
    azure_vision_key: str = Field(default="", alias="AZURE_VISION_KEY")

    # --- Azure AI Translator ---
    azure_translator_endpoint: str = Field(
        default="https://api.cognitive.microsofttranslator.com/",
        alias="AZURE_TRANSLATOR_ENDPOINT",
    )
    azure_translator_key: str = Field(default="", alias="AZURE_TRANSLATOR_KEY")
    azure_translator_region: str = Field(
        default="eastus", alias="AZURE_TRANSLATOR_REGION"
    )

    # --- Azure AI Search ---
    azure_search_endpoint: str = Field(default="", alias="AZURE_SEARCH_ENDPOINT")
    azure_search_admin_key: str = Field(default="", alias="AZURE_SEARCH_ADMIN_KEY")
    azure_search_index_name: str = Field(
        default="documents-index", alias="AZURE_SEARCH_INDEX_NAME"
    )

    # --- Azure AI Content Safety ---
    azure_content_safety_endpoint: str = Field(
        default="", alias="AZURE_CONTENT_SAFETY_ENDPOINT"
    )
    azure_content_safety_key: str = Field(
        default="", alias="AZURE_CONTENT_SAFETY_KEY"
    )

    # --- Azure Blob Storage ---
    azure_storage_connection_string: str = Field(
        default="", alias="AZURE_STORAGE_CONNECTION_STRING"
    )
    azure_storage_container_name: str = Field(
        default="documents", alias="AZURE_STORAGE_CONTAINER_NAME"
    )

    # --- Application Settings ---
    app_env: str = Field(default="development", alias="APP_ENV")
    app_host: str = Field(default="0.0.0.0", alias="APP_HOST")
    app_port: int = Field(default=8000, alias="APP_PORT")
    max_upload_size_mb: int = Field(default=50, alias="MAX_UPLOAD_SIZE_MB")
    allowed_extensions: str = Field(
        default="pdf,docx,txt,png,jpg,jpeg,tiff", alias="ALLOWED_EXTENSIONS"
    )

    model_config = {"env_file": ".env", "populate_by_name": True}

    @property
    def allowed_extensions_list(self) -> list[str]:
        return [ext.strip() for ext in self.allowed_extensions.split(",")]

    @property
    def max_upload_size_bytes(self) -> int:
        return self.max_upload_size_mb * 1024 * 1024


@lru_cache
def get_settings() -> Settings:
    return Settings()

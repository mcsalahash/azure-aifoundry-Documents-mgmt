"""
Application configuration with Azure Key Vault support.

Secret loading priority:
  1. Azure Key Vault  (si AZURE_KEYVAULT_URL est défini)
  2. Variables d'environnement / fichier .env  (fallback développement local)

Bonnes pratiques :
  - Production (VM) : Managed Identity système → aucune clé sur disque
  - Développement local : `az login` → DefaultAzureCredential la récupère automatiquement
"""
import os
import logging
from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings

logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    # --- Key Vault -------------------------------------------------------
    # Seule valeur à mettre dans .env : l'URL du vault (pas un secret)
    azure_keyvault_url: str = Field(default="", alias="AZURE_KEYVAULT_URL")

    # --- Azure Subscription ----------------------------------------------
    azure_subscription_id: str = Field(default="", alias="AZURE_SUBSCRIPTION_ID")
    azure_resource_group: str = Field(default="", alias="AZURE_RESOURCE_GROUP")
    azure_location: str = Field(default="eastus", alias="AZURE_LOCATION")

    # --- Azure Document Intelligence -------------------------------------
    azure_document_intelligence_endpoint: str = Field(
        default="", alias="AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT"
    )
    azure_document_intelligence_key: str = Field(
        default="", alias="AZURE_DOCUMENT_INTELLIGENCE_KEY"
    )

    # --- Azure AI Language -----------------------------------------------
    azure_language_endpoint: str = Field(default="", alias="AZURE_LANGUAGE_ENDPOINT")
    azure_language_key: str = Field(default="", alias="AZURE_LANGUAGE_KEY")

    # --- Azure OpenAI ----------------------------------------------------
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

    # --- Azure AI Vision -------------------------------------------------
    azure_vision_endpoint: str = Field(default="", alias="AZURE_VISION_ENDPOINT")
    azure_vision_key: str = Field(default="", alias="AZURE_VISION_KEY")

    # --- Azure AI Translator ---------------------------------------------
    azure_translator_endpoint: str = Field(
        default="https://api.cognitive.microsofttranslator.com/",
        alias="AZURE_TRANSLATOR_ENDPOINT",
    )
    azure_translator_key: str = Field(default="", alias="AZURE_TRANSLATOR_KEY")
    azure_translator_region: str = Field(
        default="eastus", alias="AZURE_TRANSLATOR_REGION"
    )

    # --- Azure AI Search -------------------------------------------------
    azure_search_endpoint: str = Field(default="", alias="AZURE_SEARCH_ENDPOINT")
    azure_search_admin_key: str = Field(default="", alias="AZURE_SEARCH_ADMIN_KEY")
    azure_search_index_name: str = Field(
        default="documents-index", alias="AZURE_SEARCH_INDEX_NAME"
    )

    # --- Azure AI Content Safety -----------------------------------------
    azure_content_safety_endpoint: str = Field(
        default="", alias="AZURE_CONTENT_SAFETY_ENDPOINT"
    )
    azure_content_safety_key: str = Field(
        default="", alias="AZURE_CONTENT_SAFETY_KEY"
    )

    # --- Azure Blob Storage ----------------------------------------------
    azure_storage_connection_string: str = Field(
        default="", alias="AZURE_STORAGE_CONNECTION_STRING"
    )
    azure_storage_container_name: str = Field(
        default="documents", alias="AZURE_STORAGE_CONTAINER_NAME"
    )

    # --- Application Settings (non-secrets, ok en env var) ---------------
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


# Correspondance : nom du secret Key Vault → variable d'environnement Settings
# Convention Key Vault : tirets uniquement (pas d'underscores autorisés)
_KV_SECRET_MAP: dict[str, str] = {
    "azure-document-intelligence-endpoint": "AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT",
    "azure-document-intelligence-key":      "AZURE_DOCUMENT_INTELLIGENCE_KEY",
    "azure-language-endpoint":              "AZURE_LANGUAGE_ENDPOINT",
    "azure-language-key":                   "AZURE_LANGUAGE_KEY",
    "azure-openai-endpoint":                "AZURE_OPENAI_ENDPOINT",
    "azure-openai-api-key":                 "AZURE_OPENAI_API_KEY",
    "azure-vision-endpoint":                "AZURE_VISION_ENDPOINT",
    "azure-vision-key":                     "AZURE_VISION_KEY",
    "azure-translator-key":                 "AZURE_TRANSLATOR_KEY",
    "azure-search-endpoint":                "AZURE_SEARCH_ENDPOINT",
    "azure-search-admin-key":               "AZURE_SEARCH_ADMIN_KEY",
    "azure-content-safety-endpoint":        "AZURE_CONTENT_SAFETY_ENDPOINT",
    "azure-content-safety-key":             "AZURE_CONTENT_SAFETY_KEY",
    "azure-storage-connection-string":      "AZURE_STORAGE_CONNECTION_STRING",
}


def _inject_keyvault_secrets(kv_url: str) -> None:
    """
    Récupère tous les secrets depuis Key Vault et les injecte dans os.environ
    pour que pydantic-settings les lise normalement.

    DefaultAzureCredential tente dans l'ordre :
      - EnvironmentCredential      (AZURE_CLIENT_ID / TENANT_ID / CLIENT_SECRET)
      - WorkloadIdentityCredential (Kubernetes)
      - ManagedIdentityCredential  (VM / App Service / Container)  ← production
      - AzureCliCredential         (az login)                       ← développement local
      - et plusieurs autres...
    """
    try:
        from azure.identity import DefaultAzureCredential
        from azure.keyvault.secrets import SecretClient
        from azure.core.exceptions import ResourceNotFoundError
    except ImportError as exc:
        raise ImportError(
            "azure-keyvault-secrets est requis. Lancez : pip install azure-keyvault-secrets"
        ) from exc

    credential = DefaultAzureCredential()
    client = SecretClient(vault_url=kv_url, credential=credential)
    loaded, missing = 0, 0

    for secret_name, env_name in _KV_SECRET_MAP.items():
        try:
            secret = client.get_secret(secret_name)
            os.environ[env_name] = secret.value
            loaded += 1
        except ResourceNotFoundError:
            missing += 1
            logger.debug("Secret Key Vault non trouvé : %s (ignoré)", secret_name)
        except Exception as exc:
            logger.warning("Impossible de lire %s depuis Key Vault : %s", secret_name, exc)

    logger.info(
        "Key Vault '%s' : %d secrets chargés, %d absents.", kv_url, loaded, missing
    )


@lru_cache
def get_settings() -> Settings:
    # Lire l'URL du vault depuis l'env (pas encore chargé dans Settings)
    kv_url = os.getenv("AZURE_KEYVAULT_URL", "")
    if kv_url:
        _inject_keyvault_secrets(kv_url)
    else:
        logger.warning(
            "AZURE_KEYVAULT_URL non défini — utilisation des variables d'environnement locales. "
            "Ne jamais utiliser ce mode en production."
        )
    return Settings()

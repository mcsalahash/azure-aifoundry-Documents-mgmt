"""
Azure OpenAI Service (AI-102)
=================================
Covers:
  - Chat completions with GPT-4o
  - Document Q&A (Retrieval-Augmented Generation concept)
  - Document summarization via LLM
  - Document generation
  - Embedding generation (for semantic search)
  - Prompt engineering best practices
  - System/user/assistant message roles
"""
import logging
from typing import Optional
from openai import AzureOpenAI
from openai import APIError

from app.config import get_settings
from app.models.schemas import (
    DocumentQARequest,
    DocumentQAResponse,
    DocumentGenerationRequest,
    DocumentSummarizationRequest,
    ChatMessage,
)

logger = logging.getLogger(__name__)

DOCUMENT_QA_SYSTEM_PROMPT = """Tu es un assistant expert en analyse de documents.
Tu réponds aux questions en te basant UNIQUEMENT sur le contenu du document fourni.
Si la réponse ne se trouve pas dans le document, dis-le clairement.
Tes réponses sont précises, concises et en français sauf si l'utilisateur demande autre chose.
Tu cites les parties pertinentes du document pour appuyer tes réponses."""

DOCUMENT_SUMMARY_SYSTEM_PROMPT = """Tu es un expert en synthèse de documents.
Tu génères des résumés clairs, structurés et fidèles au document original.
Le résumé doit capturer les points essentiels, les décisions clés et les informations critiques."""

DOCUMENT_GENERATION_SYSTEM_PROMPT = """Tu es un rédacteur professionnel expert en rédaction de documents formels.
Tu génères des documents bien structurés, professionnels et adaptés au contexte demandé.
Utilise un langage approprié au type de document."""


class AzureOpenAIService:
    """
    Wraps Azure OpenAI SDK for document intelligence tasks.

    AI-102 Skills covered:
    - Configure and use Azure OpenAI deployments
    - Implement chat completions with system/user/assistant roles
    - Design effective prompts (prompt engineering)
    - Implement RAG pattern for document Q&A
    - Generate embeddings for semantic similarity
    - Handle token limits and streaming
    """

    def __init__(self):
        settings = get_settings()
        self.client = AzureOpenAI(
            azure_endpoint=settings.azure_openai_endpoint,
            api_key=settings.azure_openai_api_key,
            api_version=settings.azure_openai_api_version,
        )
        self.chat_deployment = settings.azure_openai_chat_deployment
        self.embedding_deployment = settings.azure_openai_embedding_deployment

    async def answer_document_question(
        self, request: DocumentQARequest
    ) -> DocumentQAResponse:
        """
        Answer a question about a document using RAG pattern.

        AI-102 concept: Retrieval-Augmented Generation (RAG) combines
        document retrieval with generative AI. The document content is
        injected into the prompt as context, allowing the model to answer
        questions grounded in the document.

        Args:
            request: Contains the question, document context, and chat history.

        Returns:
            AI-generated answer with token usage.
        """
        messages = [
            {
                "role": "system",
                "content": DOCUMENT_QA_SYSTEM_PROMPT,
            },
            {
                "role": "user",
                "content": f"Voici le contenu du document:\n\n{request.document_context}\n\n---\n\nQuestion: {request.question}",
            },
        ]

        # Add chat history for multi-turn conversation (AI-102: conversation management)
        if request.chat_history:
            # Insert history before the current question
            history_messages = [
                {"role": msg.role, "content": msg.content}
                for msg in request.chat_history
            ]
            messages = [messages[0]] + history_messages + [messages[1]]

        try:
            response = self.client.chat.completions.create(
                model=self.chat_deployment,
                messages=messages,
                max_tokens=request.max_tokens,
                temperature=request.temperature,
            )

            answer = response.choices[0].message.content or ""
            tokens_used = response.usage.total_tokens if response.usage else 0

            return DocumentQAResponse(
                answer=answer,
                tokens_used=tokens_used,
                model=self.chat_deployment,
            )

        except APIError as e:
            logger.error("Azure OpenAI API error: %s", str(e))
            raise

    async def summarize_document(
        self, request: DocumentSummarizationRequest
    ) -> str:
        """
        Generate an AI-powered document summary.

        AI-102 concept: Prompt engineering for different summary lengths
        and styles. Temperature controls creativity vs. precision.

        Args:
            request: Contains text, desired summary length, and language.

        Returns:
            Generated summary text.
        """
        length_instructions = {
            "short": "en 2-3 phrases clés (maximum 150 mots)",
            "medium": "en un paragraphe structuré (200-400 mots)",
            "long": "en plusieurs sections organisées avec titres (400-800 mots)",
        }
        length_instruction = length_instructions.get(request.summary_length, length_instructions["medium"])

        prompt = f"""Génère un résumé {length_instruction} du document suivant.
Le résumé doit être en {request.language}.

Document:
{request.text}"""

        response = self.client.chat.completions.create(
            model=self.chat_deployment,
            messages=[
                {"role": "system", "content": DOCUMENT_SUMMARY_SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            max_tokens=1500,
            temperature=0.2,
        )
        return response.choices[0].message.content or ""

    async def generate_document(
        self, request: DocumentGenerationRequest
    ) -> str:
        """
        Generate a new document based on instructions.

        AI-102 concept: Using structured prompts to generate professional
        documents. Temperature tuning for different document types.

        Args:
            request: Document type, instructions, and language.

        Returns:
            Generated document content in Markdown.
        """
        prompt = f"""Génère un {request.document_type} en {request.language} selon les instructions suivantes:

{request.instructions}

Le document doit être complet, professionnel et formaté en Markdown."""

        response = self.client.chat.completions.create(
            model=self.chat_deployment,
            messages=[
                {"role": "system", "content": DOCUMENT_GENERATION_SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            max_tokens=request.max_tokens,
            temperature=0.5,
        )
        return response.choices[0].message.content or ""

    async def classify_document(self, text: str) -> dict:
        """
        Classify a document by type and topics using zero-shot classification.

        AI-102 concept: Zero-shot classification uses LLMs to classify text
        without fine-tuning, by describing categories in the prompt.

        Returns:
            Dictionary with document type, topics, and confidence.
        """
        prompt = f"""Analyse ce document et fournis une classification JSON avec:
- "type": type de document (contrat, facture, rapport, courrier, formulaire, autre)
- "domain": domaine (juridique, financier, médical, technique, commercial, RH, autre)
- "topics": liste des sujets principaux (max 5)
- "language": langue principale du document
- "formality": niveau de formalité (formel, semi-formel, informel)
- "confidentiality": niveau de confidentialité estimé (public, interne, confidentiel, secret)

Document (extrait):
{text[:2000]}

Réponds uniquement avec le JSON, sans texte supplémentaire."""

        response = self.client.chat.completions.create(
            model=self.chat_deployment,
            messages=[
                {"role": "system", "content": "Tu es un classificateur de documents. Réponds uniquement en JSON valide."},
                {"role": "user", "content": prompt},
            ],
            max_tokens=500,
            temperature=0.1,
            response_format={"type": "json_object"},
        )

        import json
        try:
            return json.loads(response.choices[0].message.content or "{}")
        except json.JSONDecodeError:
            return {"type": "unknown", "domain": "unknown", "topics": []}

    async def generate_embeddings(self, texts: list[str]) -> list[list[float]]:
        """
        Generate text embeddings for semantic search.

        AI-102 concept: Embeddings are numerical representations of text
        that capture semantic meaning. Similar texts have similar embeddings,
        enabling semantic search and clustering.

        Args:
            texts: List of texts to embed.

        Returns:
            List of embedding vectors.
        """
        response = self.client.embeddings.create(
            model=self.embedding_deployment,
            input=texts,
        )
        return [item.embedding for item in response.data]

    async def chat_with_history(
        self,
        messages: list[ChatMessage],
        system_prompt: Optional[str] = None,
        max_tokens: int = 1000,
        temperature: float = 0.7,
    ) -> str:
        """
        Multi-turn conversation with the AI assistant.

        AI-102 concept: Managing conversation history using the
        system/user/assistant message format for context-aware responses.

        Args:
            messages: Full conversation history.
            system_prompt: Optional custom system prompt.
            max_tokens: Maximum response length.
            temperature: Response creativity (0=deterministic, 2=creative).

        Returns:
            AI response text.
        """
        api_messages = []
        if system_prompt:
            api_messages.append({"role": "system", "content": system_prompt})

        for msg in messages:
            api_messages.append({"role": msg.role, "content": msg.content})

        response = self.client.chat.completions.create(
            model=self.chat_deployment,
            messages=api_messages,
            max_tokens=max_tokens,
            temperature=temperature,
        )
        return response.choices[0].message.content or ""

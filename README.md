# Azure AI Foundry — Gestion Intelligente de Documents

Application de référence pour la **certification Microsoft AI-102**, couvrant l'ensemble des services Azure AI via un cas d'usage concret de gestion documentaire.

## Services Azure AI intégrés (AI-102)

| Service | Compétences AI-102 | Endpoints |
|---------|-------------------|-----------|
| **Document Intelligence** | Modèles pré-construits, extraction KV, tableaux | `POST /api/v1/documents/analyze` |
| **Azure AI Language** | Sentiment, NER, PII, résumé, détection de langue | `POST /api/v1/analysis/nlp` |
| **Azure OpenAI** | RAG, prompt engineering, génération, embeddings | `POST /api/v1/analysis/qa` |
| **Azure AI Vision** | OCR, légendes, objets, personnes, tags | `POST /api/v1/documents/ocr` |
| **Azure AI Translator** | Traduction multi-langues, translittération | `POST /api/v1/analysis/translate` |
| **Azure AI Content Safety** | Modération texte/image, sévérité 0-6 | `POST /api/v1/analysis/safety` |
| **Azure AI Search** | Recherche sémantique, vectorielle, filtres | `POST /api/v1/search/query` |

## Structure du projet

```
azure-aifoundry-Documents-mgmt/
├── app/
│   ├── main.py                    # FastAPI application
│   ├── config.py                  # Configuration (Pydantic Settings)
│   ├── models/schemas.py          # Pydantic request/response models
│   ├── services/
│   │   ├── document_intelligence.py   # Azure AI Document Intelligence
│   │   ├── ai_language.py             # Azure AI Language (NLP)
│   │   ├── openai_service.py          # Azure OpenAI (GPT-4o, RAG)
│   │   ├── vision_service.py          # Azure AI Vision (OCR)
│   │   ├── translation_service.py     # Azure AI Translator
│   │   ├── content_safety.py          # Azure AI Content Safety
│   │   └── search_service.py          # Azure AI Search
│   ├── routers/
│   │   ├── documents.py           # Document upload & analysis routes
│   │   ├── analysis.py            # NLP, OpenAI, translation, safety routes
│   │   └── search.py              # Search & indexing routes
│   └── utils/file_handler.py      # File validation & text extraction
├── frontend/
│   ├── index.html                 # Interface web complète
│   ├── styles.css                 # Design Azure Fluent-inspired
│   └── app.js                     # Interactions JavaScript
├── notebooks/
│   ├── 01_document_intelligence.ipynb
│   ├── 02_ai_language.ipynb
│   ├── 03_azure_openai.ipynb
│   ├── 04_computer_vision.ipynb
│   ├── 05_translation.ipynb
│   ├── 06_ai_search.ipynb
│   └── 07_content_safety.ipynb
├── scripts/
│   └── setup_azure_resources.sh  # Provisioning Azure CLI
├── tests/
│   ├── test_schemas.py
│   └── test_api.py
├── .env.example
├── requirements.txt
├── Dockerfile
└── docker-compose.yml
```

## Démarrage rapide

### 1. Provisionner les ressources Azure

```bash
chmod +x scripts/setup_azure_resources.sh
./scripts/setup_azure_resources.sh
```

### 2. Configurer l'environnement

```bash
cp .env.example .env
# Remplir les valeurs dans .env
```

### 3. Installer et lancer

```bash
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 4. Avec Docker

```bash
docker-compose up --build
```

### 5. Accès

- **Interface web**: http://localhost:8000
- **API Swagger**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **Health check**: http://localhost:8000/health

## Labs Jupyter — AI-102

Chaque notebook couvre un service Azure AI avec des explications détaillées:

```bash
pip install jupyter
jupyter notebook notebooks/
```

| Notebook | Service | Compétences clés |
|----------|---------|-----------------|
| `01_document_intelligence.ipynb` | Document Intelligence | Modèles pré-construits, KV pairs, tableaux |
| `02_ai_language.ipynb` | AI Language | Sentiment, NER, PII, résumé |
| `03_azure_openai.ipynb` | Azure OpenAI | RAG, chat multi-tours, embeddings |
| `04_computer_vision.ipynb` | AI Vision | OCR, légendes, smart crops |
| `05_translation.ipynb` | Translator | Traduction, translittération, dictionnaire |
| `06_ai_search.ipynb` | AI Search | Index, recherche sémantique, filtres |
| `07_content_safety.ipynb` | Content Safety | Modération, sévérité, jailbreak |

## Pipeline d'analyse complet

L'endpoint `POST /api/v1/analysis/analyze-file` orchestre tous les services:

```
Fichier uploadé
    ↓
Extraction de texte (Document Intelligence / PyMuPDF)
    ↓
Analyse NLP (AI Language: langue, sentiment, entités)
    ↓
Classification (Azure OpenAI: type, domaine, sujets)
    ↓
Modération (Content Safety: 4 catégories)
    ↓
Résumé (AI Language: abstractif + extractif)
    ↓
Rapport JSON complet
```

## Couverture AI-102

Cette application couvre les domaines suivants de l'examen AI-102:

- ✅ Planifier et gérer une solution Azure AI
- ✅ Implémenter des solutions de vision par ordinateur
- ✅ Implémenter des solutions de traitement du langage naturel
- ✅ Implémenter des solutions de knowledge mining et Document Intelligence
- ✅ Implémenter des solutions d'IA générative
- ✅ Sécurité et responsabilité de l'IA (Content Safety)

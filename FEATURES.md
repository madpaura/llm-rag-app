# RAG Application Features

Comprehensive documentation of all features, ingestion techniques, and RAG strategies.

## Table of Contents

- [Ingestion Techniques](#ingestion-techniques)
  - [Code Ingestion](#code-ingestion)
  - [Document Ingestion](#document-ingestion)
  - [Wiki/Confluence Ingestion](#wikiconfluence-ingestion)
- [RAG Techniques](#rag-techniques)
  - [Standard RAG](#1-standard-rag)
  - [RAG-Fusion](#2-rag-fusion)
  - [HyDE](#3-hyde-hypothetical-document-embeddings)
  - [Multi-Query](#4-multi-query)
- [Embedding Strategies](#embedding-strategies)
- [Retrieval Strategies](#retrieval-strategies)

---

## Ingestion Techniques

### Code Ingestion

The system provides intelligent code ingestion with AST-based parsing and LLM-powered summarization.

#### Code Ingestion Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         CODE INGESTION PIPELINE                              │
└─────────────────────────────────────────────────────────────────────────────┘

┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│  Git Clone   │     │   Direct     │     │   File       │
│  Repository  │     │   Upload     │     │   System     │
└──────┬───────┘     └──────┬───────┘     └──────┬───────┘
       │                    │                    │
       └────────────────────┼────────────────────┘
                            │
                            ▼
               ┌────────────────────────┐
               │   File Type Detection  │
               │   (.c, .cpp, .h, .py)  │
               └───────────┬────────────┘
                           │
                           ▼
               ┌────────────────────────┐
               │   Tree-sitter Parser   │
               │   (AST Generation)     │
               └───────────┬────────────┘
                           │
                           ▼
               ┌────────────────────────┐
               │   Code Unit Extraction │
               │   - Functions          │
               │   - Classes            │
               │   - Structs            │
               │   - Methods            │
               └───────────┬────────────┘
                           │
         ┌─────────────────┼─────────────────┐
         │                 │                 │
         ▼                 ▼                 ▼
┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
│ Function Summary│ │  Class Summary  │ │  File Summary   │
│   Generation    │ │   Generation    │ │   Generation    │
│     (LLM)       │ │     (LLM)       │ │     (LLM)       │
└────────┬────────┘ └────────┬────────┘ └────────┬────────┘
         │                   │                   │
         └───────────────────┼───────────────────┘
                             │
                             ▼
               ┌────────────────────────┐
               │   Call Graph Builder   │
               │   (Dependency Links)   │
               └───────────┬────────────┘
                           │
                           ▼
               ┌────────────────────────┐
               │   Embedding Creation   │
               │   (Summary + Code)     │
               └───────────┬────────────┘
                           │
                           ▼
               ┌────────────────────────┐
               │   Vector Store +       │
               │   Database Storage     │
               └────────────────────────┘
```

#### Supported Languages

| Language | Extensions | Parser | Features |
|----------|------------|--------|----------|
| **C** | `.c`, `.h` | tree-sitter-c | Functions, Structs, Includes |
| **C++** | `.cpp`, `.cc`, `.hpp`, `.hxx` | tree-sitter-cpp | Classes, Methods, Templates |
| **Python** | `.py` | Built-in | Functions, Classes, Decorators |
| **JavaScript** | `.js`, `.jsx` | Built-in | Functions, Classes, Exports |
| **TypeScript** | `.ts`, `.tsx` | Built-in | Interfaces, Types, Classes |

#### Code Unit Extraction

For each code file, the system extracts:

1. **Functions/Methods**
   - Name and signature
   - Parameters and return type
   - Full source code
   - Function calls (for call graph)

2. **Classes**
   - Class name and inheritance
   - Member methods
   - Member variables
   - Nested classes

3. **Structs**
   - Struct name
   - Member fields
   - Associated functions

#### Hierarchical Summary Generation

```
┌─────────────────────────────────────────────────────────────────┐
│                    SUMMARY HIERARCHY                             │
└─────────────────────────────────────────────────────────────────┘

                    ┌─────────────────┐
                    │  File Summary   │
                    │  "This file     │
                    │   implements... │
                    └────────┬────────┘
                             │
            ┌────────────────┼────────────────┐
            │                │                │
            ▼                ▼                ▼
   ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
   │ Class Summary   │ │ Struct Summary  │ │ Function Summary│
   │ "Manages the    │ │ "Data structure │ │ "Initializes    │
   │  connection..." │ │  for config..." │ │  the system..." │
   └────────┬────────┘ └─────────────────┘ └─────────────────┘
            │
   ┌────────┼────────┐
   │        │        │
   ▼        ▼        ▼
┌──────┐ ┌──────┐ ┌──────┐
│Method│ │Method│ │Method│
│ Sum  │ │ Sum  │ │ Sum  │
└──────┘ └──────┘ └──────┘
```

Summaries are generated bottom-up:
1. **Function/Method summaries** - Generated first from code
2. **Class summaries** - Generated using method summaries
3. **File summaries** - Generated using all child summaries

#### Call Graph Analysis

```
┌─────────────────────────────────────────────────────────────────┐
│                      CALL GRAPH EXAMPLE                          │
└─────────────────────────────────────────────────────────────────┘

    main.c                          utils.c
    ┌─────────────────┐             ┌─────────────────┐
    │     main()      │────────────▶│   init_system() │
    └────────┬────────┘             └────────┬────────┘
             │                               │
             │                               ▼
             │                      ┌─────────────────┐
             │                      │  load_config()  │
             │                      └─────────────────┘
             │
             ▼
    ┌─────────────────┐
    │  process_data() │────────────▶ validate_input()
    └────────┬────────┘
             │
             ▼
    ┌─────────────────┐
    │   cleanup()     │
    └─────────────────┘
```

#### API Endpoints for Code Ingestion

```bash
# Ingest from Git repository
POST /api/ingestion/git
{
  "workspace_id": 1,
  "name": "my-project",
  "repo_url": "https://github.com/org/repo.git",
  "branch": "main"
}

# Ingest from local directory
POST /api/ingestion/code/directory
{
  "workspace_id": 1,
  "directory": "/path/to/code",
  "recursive": true,
  "max_depth": 3,
  "include_headers": true
}

# Upload code files
POST /api/ingestion/upload
Content-Type: multipart/form-data
files: [file1.c, file2.cpp, ...]
workspace_id: 1
```

---

### Document Ingestion

Standard document processing for non-code files.

#### Document Ingestion Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                       DOCUMENT INGESTION PIPELINE                            │
└─────────────────────────────────────────────────────────────────────────────┘

┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│     PDF      │     │   Markdown   │     │    DOCX      │
│    Files     │     │    Files     │     │    Files     │
└──────┬───────┘     └──────┬───────┘     └──────┬───────┘
       │                    │                    │
       └────────────────────┼────────────────────┘
                            │
                            ▼
               ┌────────────────────────┐
               │    Text Extraction     │
               │  (PyPDF2, python-docx) │
               └───────────┬────────────┘
                           │
                           ▼
               ┌────────────────────────┐
               │   Content Cleaning     │
               │   - Remove artifacts   │
               │   - Normalize spacing  │
               └───────────┬────────────┘
                           │
                           ▼
               ┌────────────────────────┐
               │   Text Chunking        │
               │   - Size: 1000 chars   │
               │   - Overlap: 200 chars │
               └───────────┬────────────┘
                           │
                           ▼
               ┌────────────────────────┐
               │   Metadata Extraction  │
               │   - Title, Author      │
               │   - Page numbers       │
               └───────────┬────────────┘
                           │
                           ▼
               ┌────────────────────────┐
               │   Embedding Creation   │
               │   (nomic-embed-text)   │
               └───────────┬────────────┘
                           │
                           ▼
               ┌────────────────────────┐
               │   Vector Store +       │
               │   Database Storage     │
               └────────────────────────┘
```

#### Supported Document Types

| Format | Extension | Extractor | Notes |
|--------|-----------|-----------|-------|
| **PDF** | `.pdf` | PyPDF2 | Text extraction, page tracking |
| **Markdown** | `.md` | Built-in | Preserves formatting |
| **Plain Text** | `.txt` | Built-in | Direct processing |
| **Word** | `.docx` | python-docx | Full document support |
| **RST** | `.rst` | Built-in | ReStructuredText |
| **YAML/JSON** | `.yaml`, `.json` | Built-in | Config documentation |

#### Chunking Strategy

```
┌─────────────────────────────────────────────────────────────────┐
│                     CHUNKING VISUALIZATION                       │
└─────────────────────────────────────────────────────────────────┘

Original Document (3000 characters):
┌─────────────────────────────────────────────────────────────────┐
│ Lorem ipsum dolor sit amet, consectetur adipiscing elit...      │
│ ... (content continues) ...                                      │
│ ... (more content) ...                                           │
└─────────────────────────────────────────────────────────────────┘

After Chunking (1000 char chunks, 200 char overlap):

Chunk 1 (chars 0-1000):
┌─────────────────────────────────────────────────────────────────┐
│ Lorem ipsum dolor sit amet, consectetur adipiscing elit...      │
│ ... (800 unique chars) ... ████████████████████████████████████ │
│                            ▲                                     │
│                            └── 200 char overlap with Chunk 2     │
└─────────────────────────────────────────────────────────────────┘

Chunk 2 (chars 800-1800):
┌─────────────────────────────────────────────────────────────────┐
│ ████████████████████████████ ... (800 unique chars) ...         │
│ ▲                            ████████████████████████████████████│
│ └── 200 char overlap         ▲                                   │
│     from Chunk 1             └── 200 char overlap with Chunk 3   │
└─────────────────────────────────────────────────────────────────┘

Chunk 3 (chars 1600-2600):
┌─────────────────────────────────────────────────────────────────┐
│ ████████████████████████████ ... (800 unique chars) ...         │
│ ▲                            ████████████████████████████████████│
│ └── 200 char overlap from Chunk 2                                │
└─────────────────────────────────────────────────────────────────┘
```

**Why Overlap?**
- Preserves context across chunk boundaries
- Prevents information loss at split points
- Improves retrieval accuracy for queries spanning chunks

---

### Wiki/Confluence Ingestion

Import documentation from Confluence wikis.

#### Confluence Ingestion Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                      CONFLUENCE INGESTION PIPELINE                           │
└─────────────────────────────────────────────────────────────────────────────┘

┌──────────────────┐
│  Confluence API  │
│  (Space/Page ID) │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│  Authentication  │
│  (API Token)     │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│  Page Retrieval  │
│  - Content       │
│  - Attachments   │
│  - Child pages   │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│  HTML → Markdown │
│  Conversion      │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│  Standard Doc    │
│  Pipeline        │
│  (Chunk/Embed)   │
└──────────────────┘
```

#### API Endpoint

```bash
POST /api/ingestion/confluence
{
  "workspace_id": 1,
  "name": "team-wiki",
  "confluence_url": "https://company.atlassian.net",
  "space_key": "TEAM",
  "api_token": "your-api-token",
  "include_children": true
}
```

---

## RAG Techniques

### 1. Standard RAG

The classic retrieve-then-generate approach.

#### Flow Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           STANDARD RAG FLOW                                  │
└─────────────────────────────────────────────────────────────────────────────┘

┌──────────────┐
│  User Query  │
│ "How do I    │
│  configure   │
│  logging?"   │
└──────┬───────┘
       │
       ▼
┌──────────────────┐
│  Query Embedding │
│  (nomic-embed)   │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│  Vector Search   │
│  (FAISS)         │
│  Top-K = 5       │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│  Retrieved Docs  │
│  [Doc1, Doc2,    │
│   Doc3, Doc4,    │
│   Doc5]          │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│  Context Assembly│
│  + Prompt Build  │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│  LLM Generation  │
│  (Ollama)        │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│  Answer +        │
│  Citations       │
└──────────────────┘
```

#### When to Use
- Simple, direct questions
- Questions with clear answers in documents
- Fast response time needed

#### Example

```python
# Request
{
  "question": "How do I configure logging?",
  "workspace_id": 1,
  "rag_technique": "standard",
  "k": 5
}

# Response
{
  "answer": "To configure logging, you need to...",
  "sources": [
    {"file": "config.md", "chunk": 3, "score": 0.92},
    {"file": "setup.md", "chunk": 1, "score": 0.87}
  ],
  "technique": "standard"
}
```

---

### 2. RAG-Fusion

Generates multiple query variations and combines results using Reciprocal Rank Fusion.

#### Flow Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           RAG-FUSION FLOW                                    │
└─────────────────────────────────────────────────────────────────────────────┘

┌──────────────────┐
│   User Query     │
│  "How to debug   │
│   memory leaks?" │
└────────┬─────────┘
         │
         ▼
┌──────────────────────────────────────────────────────────────┐
│                  LLM Query Generation                         │
│  Generate 3-5 semantically similar queries                    │
└──────────────────────────────────────────────────────────────┘
         │
         ├──────────────────┬──────────────────┬──────────────────┐
         │                  │                  │                  │
         ▼                  ▼                  ▼                  ▼
┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
│ "memory leak    │ │ "find memory    │ │ "valgrind       │ │ "heap analysis  │
│  debugging"     │ │  issues"        │ │  tutorial"      │ │  tools"         │
└────────┬────────┘ └────────┬────────┘ └────────┬────────┘ └────────┬────────┘
         │                   │                   │                   │
         ▼                   ▼                   ▼                   ▼
┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
│ Vector Search   │ │ Vector Search   │ │ Vector Search   │ │ Vector Search   │
│ Results: A,B,C  │ │ Results: B,D,E  │ │ Results: A,E,F  │ │ Results: C,D,G  │
└────────┬────────┘ └────────┬────────┘ └────────┬────────┘ └────────┬────────┘
         │                   │                   │                   │
         └───────────────────┼───────────────────┼───────────────────┘
                             │                   │
                             ▼                   │
               ┌─────────────────────────────────┴─┐
               │     Reciprocal Rank Fusion (RRF)  │
               │                                   │
               │  Score(d) = Σ 1/(k + rank(d))     │
               │                                   │
               │  Merged & Reranked Results:       │
               │  [A, B, E, C, D, F, G]             │
               └─────────────────┬─────────────────┘
                                 │
                                 ▼
               ┌─────────────────────────────────┐
               │     Context + LLM Generation    │
               └─────────────────────────────────┘
```

#### Reciprocal Rank Fusion (RRF) Algorithm

```
For each document d appearing in any result set:
    RRF_score(d) = Σ (1 / (k + rank_i(d)))
    
Where:
    k = 60 (constant to prevent high ranks from dominating)
    rank_i(d) = position of document d in result set i
    
Example:
    Doc A: rank 1 in Q1, rank 3 in Q3
    RRF(A) = 1/(60+1) + 1/(60+3) = 0.0164 + 0.0159 = 0.0323
    
    Doc B: rank 2 in Q1, rank 1 in Q2
    RRF(B) = 1/(60+2) + 1/(60+1) = 0.0161 + 0.0164 = 0.0325
    
    Result: B ranks higher than A
```

#### When to Use
- Complex queries with multiple aspects
- Questions that could be phrased many ways
- When standard RAG misses relevant documents

---

### 3. HyDE (Hypothetical Document Embeddings)

Generates a hypothetical answer first, then searches for similar real documents.

#### Flow Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              HyDE FLOW                                       │
└─────────────────────────────────────────────────────────────────────────────┘

┌──────────────────┐
│   User Query     │
│  "What is the    │
│   architecture   │
│   of the cache?" │
└────────┬─────────┘
         │
         ▼
┌──────────────────────────────────────────────────────────────┐
│              LLM: Generate Hypothetical Answer                │
│                                                               │
│  "The cache architecture consists of a multi-tier system     │
│   with L1, L2, and L3 levels. The L1 cache is closest to     │
│   the CPU and provides the fastest access times..."          │
└──────────────────────────────────────────────────────────────┘
         │
         ▼
┌──────────────────┐
│  Embed the       │
│  Hypothetical    │
│  Answer          │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│  Vector Search   │
│  (Find docs      │
│   similar to     │
│   hypothesis)    │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│  Retrieved Real  │
│  Documents       │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│  LLM Generation  │
│  (Using real     │
│   documents)     │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│  Final Answer    │
│  (Grounded in    │
│   real docs)     │
└──────────────────┘
```

#### Why HyDE Works

```
┌─────────────────────────────────────────────────────────────────┐
│                    EMBEDDING SPACE VISUALIZATION                 │
└─────────────────────────────────────────────────────────────────┘

                    Query: "cache architecture"
                              │
                              ▼
                           ┌─────┐
                           │  Q  │  ← Query embedding
                           └─────┘
                              
                              ↓ (far in embedding space)
                              
    ┌─────┐                           ┌─────┐
    │ D1  │ Cache implementation      │ D2  │ Memory hierarchy
    └─────┘                           └─────┘
    
                    ┌─────┐
                    │ D3  │ Architecture overview
                    └─────┘

With HyDE:
                    Hypothetical Answer
                              │
                              ▼
                           ┌─────┐
                           │  H  │  ← Hypothesis embedding
                           └─────┘
                              ↓ (close in embedding space!)
                              
    ┌─────┐                           ┌─────┐
    │ D1  │ ←── Similar! ───────────→ │ D2  │
    └─────┘                           └─────┘
```

The hypothetical answer is in the same "language" as the documents, making similarity search more effective.

#### When to Use
- Conceptual or architectural questions
- When query terms don't match document vocabulary
- Questions requiring synthesis of information

---

### 4. Multi-Query

Decomposes complex questions into sub-questions, retrieves for each, then synthesizes.

#### Flow Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          MULTI-QUERY FLOW                                    │
└─────────────────────────────────────────────────────────────────────────────┘

┌────────────────────────────────────────┐
│           Complex User Query            │
│  "How do I set up the project, what    │
│   are the dependencies, and how do     │
│   I run the tests?"                    │
└──────────────────┬─────────────────────┘
                   │
                   ▼
┌────────────────────────────────────────┐
│       LLM: Query Decomposition          │
│                                         │
│  Identify distinct sub-questions:       │
└──────────────────┬─────────────────────┘
                   │
     ┌─────────────┼─────────────┐
     │             │             │
     ▼             ▼             ▼
┌──────────┐ ┌──────────┐ ┌──────────┐
│  Sub-Q1  │ │  Sub-Q2  │ │  Sub-Q3  │
│ "How to  │ │ "What    │ │ "How to  │
│  set up  │ │  are the │ │  run     │
│  project"│ │  deps?"  │ │  tests?" │
└────┬─────┘ └────┬─────┘ └────┬─────┘
     │            │            │
     ▼            ▼            ▼
┌──────────┐ ┌──────────┐ ┌──────────┐
│ Retrieve │ │ Retrieve │ │ Retrieve │
│ Context1 │ │ Context2 │ │ Context3 │
└────┬─────┘ └────┬─────┘ └────┬─────┘
     │            │            │
     └────────────┼────────────┘
                  │
                  ▼
┌────────────────────────────────────────┐
│         Combine All Contexts            │
│  [Setup docs, Dependency list,          │
│   Test documentation]                   │
└──────────────────┬─────────────────────┘
                   │
                   ▼
┌────────────────────────────────────────┐
│       LLM: Synthesize Answer            │
│                                         │
│  Generate comprehensive response        │
│  addressing all sub-questions           │
└──────────────────┬─────────────────────┘
                   │
                   ▼
┌────────────────────────────────────────┐
│         Structured Answer               │
│                                         │
│  1. Project Setup: ...                  │
│  2. Dependencies: ...                   │
│  3. Running Tests: ...                  │
└────────────────────────────────────────┘
```

#### When to Use
- Multi-part questions
- Questions requiring information from different sources
- Comprehensive "how-to" queries

---

## Embedding Strategies

### Available Embedding Models

| Provider | Model | Dimensions | Best For |
|----------|-------|------------|----------|
| **Ollama** | nomic-embed-text | 768 | General purpose, local |
| **OpenAI** | text-embedding-ada-002 | 1536 | High quality, cloud |
| **Sentence Transformers** | all-MiniLM-L6-v2 | 384 | Fast, lightweight |

### Embedding Configuration

```python
# In config.py
EMBEDDING_PROVIDER = "ollama"  # ollama, openai, sentence_transformers
OLLAMA_EMBEDDING_MODEL = "nomic-embed-text"
```

---

## Retrieval Strategies

### Similarity Search

Standard cosine similarity search.

```python
retrieval_strategy = "similarity"
top_k = 5
```

### MMR (Maximal Marginal Relevance)

Balances relevance with diversity to avoid redundant results.

```python
retrieval_strategy = "mmr"
top_k = 5
lambda_mult = 0.5  # 0 = max diversity, 1 = max relevance
```

### Similarity Score Threshold

Only returns documents above a minimum similarity score.

```python
retrieval_strategy = "similarity_score_threshold"
score_threshold = 0.7
```

---

## Configuration Reference

### Environment Variables

```bash
# LLM Configuration
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_LLM_MODEL=gpt-oss:20b-cloud
OLLAMA_EMBEDDING_MODEL=nomic-embed-text

# Chunking Configuration
CHUNK_SIZE=1000
CHUNK_OVERLAP=200

# Retrieval Configuration
DEFAULT_TOP_K=5
DEFAULT_RAG_TECHNIQUE=standard
```

### API Configuration Example

```python
{
  "llm_model": "llama3.2:3b",
  "llm_temperature": 0.1,
  "embedding_model": "nomic-embed-text",
  "chunk_size": 1000,
  "chunk_overlap": 200,
  "retrieval_strategy": "similarity",
  "top_k": 5,
  "rag_technique": "standard"
}
```

---

## Next Steps

See [USAGE_GUIDE.md](./USAGE_GUIDE.md) for integration and end-user documentation.

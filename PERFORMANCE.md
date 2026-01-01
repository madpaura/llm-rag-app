# Performance Optimizations

This document describes the performance optimizations implemented for multi-user scenarios.

## Table of Contents

- [Overview](#overview)
- [Database Optimizations](#database-optimizations)
- [Caching System](#caching-system)
- [Lazy Loading & Service Registry](#lazy-loading--service-registry)
- [Parallel Processing](#parallel-processing)
- [Backup & Restore](#backup--restore)
- [Configuration](#configuration)
- [API Endpoints](#api-endpoints)

---

## Overview

The following optimizations were implemented to improve performance for multi-user scenarios:

| Area | Optimization | Impact |
|------|-------------|--------|
| **Startup** | Lazy service loading | ~80% faster startup |
| **Embeddings** | LRU cache with TTL | Avoid redundant API calls |
| **Queries** | Result caching | Faster repeated queries |
| **Ingestion** | Batch processing | Higher throughput |
| **Database** | Async + connection pooling | Better concurrency |
| **Backup** | Automated backup/restore | Data safety |

---

## Database Optimizations

### Async Database Support

New async database module for better concurrency:

```python
# core/database_async.py
from core.database_async import get_async_db, AsyncSessionLocal

async with get_async_db() as session:
    result = await session.execute(query)
```

### Connection Pooling

Configured in `core/config.py`:

```python
DATABASE_POOL_SIZE = 10      # Base pool connections
DATABASE_MAX_OVERFLOW = 20   # Additional connections under load
```

### Features

- **Pool pre-ping**: Validates connections before use
- **Connection recycling**: Recycles connections after 1 hour
- **Async support**: Non-blocking database operations

---

## Caching System

### Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        CACHING LAYERS                            │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   Embedding     │     │   Query Result  │     │    General      │
│     Cache       │     │     Cache       │     │     Cache       │
├─────────────────┤     ├─────────────────┤     ├─────────────────┤
│ Max: 5000       │     │ Max: 500        │     │ Max: 2000       │
│ TTL: 2 hours    │     │ TTL: 30 min     │     │ TTL: 1 hour     │
│                 │     │                 │     │                 │
│ - Text → Vector │     │ - Search results│     │ - Misc data     │
│ - Query embeds  │     │ - RAG answers   │     │ - Config        │
└─────────────────┘     └─────────────────┘     └─────────────────┘
```

### Embedding Cache

Caches generated embeddings to avoid redundant LLM calls:

```python
from core.cache import get_embedding_cache

cache = get_embedding_cache()

# Check cache before generating
cached = cache.get_embedding(text)
if cached:
    return cached

# Generate and cache
embedding = await generate_embedding(text)
cache.set_embedding(text, embedding)
```

### Query Result Cache

Caches search results and generated answers:

```python
from core.cache import get_query_cache

cache = get_query_cache()

# Cache search results
cache.set_search_results(query, workspace_id, k, results)

# Cache generated answers
cache.set_answer(query, workspace_id, technique, answer)
```

### Cache Statistics

Monitor cache performance via API:

```bash
GET /api/admin/cache/stats
```

Response:
```json
{
  "embedding_cache": {
    "hits": 1250,
    "misses": 340,
    "size": 890,
    "hit_rate": 0.786
  },
  "query_cache": {
    "search_cache": { "hits": 450, "misses": 120 },
    "answer_cache": { "hits": 200, "misses": 80 }
  }
}
```

---

## Lazy Loading & Service Registry

### Problem

Heavy services (vector store, embeddings, LLM) slow down startup.

### Solution

Services are registered but only initialized on first use:

```
┌─────────────────────────────────────────────────────────────────┐
│                     SERVICE REGISTRY                             │
└─────────────────────────────────────────────────────────────────┘

                    Application Startup
                           │
                           ▼
              ┌────────────────────────┐
              │  Register Services     │  ← Fast (no initialization)
              │  (factories only)      │
              └───────────┬────────────┘
                          │
                          ▼
              ┌────────────────────────┐
              │  Application Ready     │  ← ~0.5s startup
              └───────────┬────────────┘
                          │
            First Request │
                          ▼
              ┌────────────────────────┐
              │  Initialize Service    │  ← On-demand
              │  (vector_service)      │
              └────────────────────────┘
```

### Usage

```python
from core.service_registry import get_service, get_registry

# Get service (initializes on first call)
vector_service = get_service("vector_service")

# Check if initialized without triggering init
registry = get_registry()
if registry.is_initialized("vector_service"):
    # Already initialized
    pass
```

### Registered Services

| Service | Lazy | Init Time |
|---------|------|-----------|
| `vector_service` | Yes | ~2-3s |
| `embedding_service` | Yes | ~1-2s |
| `ollama_service` | Yes | ~0.5s |
| `ingestion_orchestrator` | Yes | ~0.1s |
| `query_service` | Yes | ~0.1s |

---

## Parallel Processing

### Batch Embedding

Embeddings are generated in configurable batches:

```python
# Configuration
EMBEDDING_BATCH_SIZE = 32      # Texts per batch
MAX_PARALLEL_EMBEDDINGS = 4    # Concurrent batches
```

### Parallel Processor

```python
from core.parallel import get_parallel_processor, parallel_embed

processor = get_parallel_processor()

# Process items in parallel
results = await processor.map_async(
    process_func,
    items,
    batch_size=50,
    progress_callback=lambda done, total: print(f"{done}/{total}")
)

# Parallel embedding generation
embeddings = await parallel_embed(
    texts,
    embedding_func,
    batch_size=32,
    max_concurrent=4
)
```

### Ingestion Pipeline

```
┌─────────────────────────────────────────────────────────────────┐
│                  PARALLEL INGESTION PIPELINE                     │
└─────────────────────────────────────────────────────────────────┘

    Documents                    Chunks                   Embeddings
        │                          │                          │
        ▼                          ▼                          ▼
┌───────────────┐          ┌───────────────┐          ┌───────────────┐
│   Batch 1     │          │   Batch 1     │          │   Batch 1     │
│   (50 docs)   │─────────▶│   (chunks)    │─────────▶│   (32 texts)  │
└───────────────┘          └───────────────┘          └───────────────┘
        │                          │                          │
        ▼                          ▼                          ▼
┌───────────────┐          ┌───────────────┐          ┌───────────────┐
│   Batch 2     │          │   Batch 2     │          │   Batch 2     │
│   (50 docs)   │─────────▶│   (chunks)    │─────────▶│   (32 texts)  │
└───────────────┘          └───────────────┘          └───────────────┘
        │                          │                          │
        ▼                          ▼                          ▼
       ...                        ...                        ...
```

---

## Backup & Restore

### Features

- **Full backups**: Complete database snapshot
- **Compression**: Gzip compression for smaller files
- **Metadata**: JSON metadata for each backup
- **Retention**: Automatic cleanup of old backups
- **Export**: JSON export for data migration

### API Endpoints

```bash
# Create backup
POST /api/admin/backup
{
  "name": "pre-migration",  # Optional
  "compress": true
}

# List backups
GET /api/admin/backup/list

# Restore backup
POST /api/admin/backup/restore/{backup_name}

# Delete backup
DELETE /api/admin/backup/{backup_name}

# Cleanup old backups
POST /api/admin/backup/cleanup?keep_count=5

# Export data to JSON
POST /api/admin/backup/export
```

### Programmatic Usage

```python
from core.backup import get_backup_service

service = get_backup_service()

# Create backup
result = service.create_backup(name="daily", compress=True)
# Returns: {"success": True, "backup_file": "...", "metadata": {...}}

# List backups
backups = service.list_backups()

# Restore
result = service.restore_backup("daily")

# Cleanup old backups
service.cleanup_old_backups(keep_count=5)
```

---

## Configuration

### Environment Variables

Add to `.env` file:

```bash
# Database
DATABASE_POOL_SIZE=10
DATABASE_MAX_OVERFLOW=20

# Caching
EMBEDDING_CACHE_SIZE=5000
EMBEDDING_CACHE_TTL=7200
QUERY_CACHE_SIZE=500
QUERY_CACHE_TTL=1800

# Batch Processing
EMBEDDING_BATCH_SIZE=32
INGESTION_BATCH_SIZE=50
MAX_PARALLEL_EMBEDDINGS=4

# Backup
BACKUP_DIR=./data/backups
BACKUP_RETENTION_COUNT=5
AUTO_BACKUP_ENABLED=false
```

### Tuning Guidelines

| Scenario | Recommendation |
|----------|----------------|
| **High traffic** | Increase cache sizes, pool size |
| **Limited memory** | Reduce cache sizes |
| **Slow embeddings** | Increase batch size, parallel workers |
| **Many workspaces** | Increase query cache size |

---

## API Endpoints

### Admin Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/admin/backup` | Create backup |
| GET | `/api/admin/backup/list` | List backups |
| POST | `/api/admin/backup/restore/{name}` | Restore backup |
| DELETE | `/api/admin/backup/{name}` | Delete backup |
| POST | `/api/admin/backup/cleanup` | Cleanup old backups |
| POST | `/api/admin/backup/export` | Export to JSON |
| GET | `/api/admin/cache/stats` | Cache statistics |
| POST | `/api/admin/cache/cleanup` | Cleanup expired |
| POST | `/api/admin/cache/clear/embeddings` | Clear embedding cache |
| POST | `/api/admin/cache/clear/queries` | Clear query cache |
| GET | `/api/admin/services/stats` | Service registry stats |
| GET | `/api/admin/services/health` | Service health check |

---

## Monitoring

### Cache Hit Rates

Monitor cache effectiveness:

```bash
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost/rag/api/api/admin/cache/stats
```

Target hit rates:
- **Embedding cache**: > 70%
- **Query cache**: > 50%

### Service Health

Check all services:

```bash
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost/rag/api/api/admin/services/health
```

---

## Files Added/Modified

### New Files

| File | Purpose |
|------|---------|
| `core/cache.py` | LRU caching system |
| `core/backup.py` | Backup/restore functionality |
| `core/database_async.py` | Async database support |
| `core/service_registry.py` | Lazy service loading |
| `core/parallel.py` | Parallel processing utilities |
| `api/routes/admin.py` | Admin API endpoints |

### Modified Files

| File | Changes |
|------|---------|
| `core/config.py` | Added performance settings |
| `services/vector_service.py` | Added caching, batch processing |
| `main.py` | Added admin routes, optimized startup |
| `requirements.txt` | Added aiosqlite |

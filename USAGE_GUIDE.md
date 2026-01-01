# RAG Application Usage Guide

Complete guide for integrating with and using the RAG application.

## Table of Contents

- [End-User Guide](#end-user-guide)
  - [Getting Started](#getting-started)
  - [Using the Web Interface](#using-the-web-interface)
  - [Querying Your Knowledge Base](#querying-your-knowledge-base)
- [Integration Guide](#integration-guide)
  - [API Authentication](#api-authentication)
  - [API Reference](#api-reference)
  - [Code Examples](#code-examples)
  - [Webhooks & Events](#webhooks--events)

---

# End-User Guide

## Getting Started

### Accessing the Application

The RAG application is available at:

| Service | URL | Description |
|---------|-----|-------------|
| **Web UI** | `http://localhost/rag/ui` | Main user interface |
| **API Docs** | `http://localhost/rag/api/docs` | Interactive API documentation |
| **ReDoc** | `http://localhost/rag/api/redoc` | Alternative API documentation |

### Creating an Account

1. Navigate to `http://localhost/rag/ui`
2. Click **"Register"** on the login page
3. Fill in your details:
   - Email address
   - Username
   - Password (minimum 8 characters)
4. Click **"Create Account"**
5. You'll be automatically logged in

### Logging In

1. Navigate to `http://localhost/rag/ui`
2. Enter your email and password
3. Click **"Login"**
4. You'll be redirected to the dashboard

---

## Using the Web Interface

### Dashboard Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  RAG Application                                    [User Menu] [Logout]    │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                        WORKSPACES                                    │    │
│  ├─────────────────────────────────────────────────────────────────────┤    │
│  │                                                                      │    │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐               │    │
│  │  │  Project A   │  │  Project B   │  │  + Create    │               │    │
│  │  │  12 docs     │  │  8 docs      │  │    New       │               │    │
│  │  │  [Open]      │  │  [Open]      │  │              │               │    │
│  │  └──────────────┘  └──────────────┘  └──────────────┘               │    │
│  │                                                                      │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Creating a Workspace

Workspaces isolate your knowledge bases. Create separate workspaces for different projects or teams.

1. Click **"+ Create New"** on the dashboard
2. Enter a workspace name (e.g., "Backend API Docs")
3. Add an optional description
4. Click **"Create Workspace"**

### Workspace View

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  Workspace: Backend API Docs                              [Settings] [Back] │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌─────────────────┐  ┌─────────────────────────────────────────────────┐   │
│  │   DATA SOURCES  │  │                    CHAT                          │   │
│  ├─────────────────┤  ├─────────────────────────────────────────────────┤   │
│  │                 │  │                                                  │   │
│  │ 📁 Git: repo1   │  │  You: How do I configure the database?          │   │
│  │    15 files     │  │                                                  │   │
│  │                 │  │  AI: To configure the database, you need to     │   │
│  │ 📄 Upload: docs │  │      set the following environment variables:   │   │
│  │    8 files      │  │      - DATABASE_URL: Connection string          │   │
│  │                 │  │      - DB_POOL_SIZE: Connection pool size       │   │
│  │ [+ Add Source]  │  │                                                  │   │
│  │                 │  │      Source: config.md (lines 45-67)            │   │
│  │                 │  │                                                  │   │
│  │                 │  │  ────────────────────────────────────────────   │   │
│  │                 │  │                                                  │   │
│  │                 │  │  [Type your question here...]        [Send]     │   │
│  │                 │  │                                                  │   │
│  └─────────────────┘  └─────────────────────────────────────────────────┘   │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Adding Data Sources

#### Option 1: Git Repository

1. Click **"+ Add Source"**
2. Select **"Git Repository"**
3. Enter repository details:
   - **Name**: A friendly name for this source
   - **Repository URL**: `https://github.com/org/repo.git`
   - **Branch**: `main` (or your preferred branch)
4. Click **"Import"**
5. Wait for ingestion to complete (progress shown)

#### Option 2: File Upload

1. Click **"+ Add Source"**
2. Select **"Upload Files"**
3. Drag and drop files or click to browse
4. Supported formats: PDF, MD, TXT, DOCX, code files
5. Click **"Upload"**

#### Option 3: Code Directory

1. Click **"+ Add Source"**
2. Select **"Code Directory"**
3. Enter the local path to your code
4. Configure options:
   - **Recursive**: Search subdirectories
   - **Max Depth**: Limit directory depth
   - **Include Headers**: Include .h/.hpp files
5. Click **"Import"**

---

## Querying Your Knowledge Base

### Basic Queries

Simply type your question in the chat input:

```
You: How do I set up authentication?

AI: To set up authentication in this project, follow these steps:

1. Configure the JWT secret in your environment:
   ```
   JWT_SECRET=your-secret-key
   JWT_EXPIRATION=30m
   ```

2. Initialize the auth middleware in your app:
   ```python
   from auth import setup_auth
   setup_auth(app)
   ```

Sources:
- auth/README.md (lines 12-45)
- config/settings.py (lines 78-92)
```

### Choosing RAG Techniques

For advanced queries, you can select different RAG techniques:

| Technique | When to Use | Example Query |
|-----------|-------------|---------------|
| **Standard** | Simple, direct questions | "What is the default port?" |
| **RAG-Fusion** | Complex queries | "Explain the caching strategy and its configuration" |
| **HyDE** | Conceptual questions | "What is the architecture philosophy?" |
| **Multi-Query** | Multi-part questions | "How do I set up, configure, and test the API?" |

### Tips for Better Results

1. **Be Specific**: "How do I configure Redis caching?" vs "How does caching work?"
2. **Provide Context**: "In the authentication module, how do I..."
3. **Ask Follow-ups**: Build on previous answers in the same chat session
4. **Check Sources**: Always verify answers against the cited sources

### Chat Sessions

- Each workspace maintains separate chat sessions
- Chat history is preserved for context
- Start a new session for unrelated topics
- Previous sessions can be reviewed

---

# Integration Guide

## API Authentication

### Getting an Access Token

```bash
# Register a new user
curl -X POST http://localhost/rag/api/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "developer@example.com",
    "username": "developer",
    "password": "securepassword123"
  }'

# Login to get access token
curl -X POST http://localhost/rag/api/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "developer@example.com",
    "password": "securepassword123"
  }'

# Response:
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

### Using the Token

Include the token in all API requests:

```bash
curl -X GET http://localhost/rag/api/api/workspaces/ \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

### Token Expiration

- Tokens expire after 30 minutes by default
- Refresh by calling the login endpoint again
- Check token validity with `/api/auth/me`

---

## API Reference

### Base URL

```
http://localhost/rag/api
```

### Endpoints Overview

#### Authentication

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/auth/register` | Register new user |
| POST | `/api/auth/login` | Login and get token |
| GET | `/api/auth/me` | Get current user info |

#### Workspaces

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/workspaces/` | List all workspaces |
| POST | `/api/workspaces/` | Create workspace |
| GET | `/api/workspaces/{id}` | Get workspace details |
| DELETE | `/api/workspaces/{id}` | Delete workspace |

#### Ingestion

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/ingestion/git` | Ingest from Git repo |
| POST | `/api/ingestion/upload` | Upload files |
| POST | `/api/ingestion/code/directory` | Ingest code directory |
| GET | `/api/ingestion/sources/{workspace_id}` | List data sources |
| DELETE | `/api/ingestion/sources/{id}` | Delete data source |

#### Query

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/query/` | Simple query |
| POST | `/api/query/chat/message` | Chat with context |
| GET | `/api/query/chat/sessions/{workspace_id}` | List chat sessions |
| GET | `/api/query/chat/history/{session_id}` | Get chat history |

#### RAG Engine (Advanced)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/rag/techniques` | List available techniques |
| GET | `/api/rag/config` | Get current config |
| PUT | `/api/rag/config` | Update config |
| POST | `/api/rag/query` | Direct RAG query |

---

## Code Examples

### Python Client

```python
import requests
from typing import Optional, List, Dict, Any

class RAGClient:
    """Python client for the RAG API."""
    
    def __init__(self, base_url: str = "http://localhost/rag/api"):
        self.base_url = base_url
        self.token: Optional[str] = None
    
    def login(self, email: str, password: str) -> str:
        """Login and store access token."""
        response = requests.post(
            f"{self.base_url}/api/auth/login",
            json={"email": email, "password": password}
        )
        response.raise_for_status()
        self.token = response.json()["access_token"]
        return self.token
    
    def _headers(self) -> Dict[str, str]:
        """Get headers with authorization."""
        if not self.token:
            raise ValueError("Not logged in. Call login() first.")
        return {"Authorization": f"Bearer {self.token}"}
    
    def list_workspaces(self) -> List[Dict[str, Any]]:
        """List all workspaces."""
        response = requests.get(
            f"{self.base_url}/api/workspaces/",
            headers=self._headers()
        )
        response.raise_for_status()
        return response.json()
    
    def create_workspace(self, name: str, description: str = "") -> Dict[str, Any]:
        """Create a new workspace."""
        response = requests.post(
            f"{self.base_url}/api/workspaces/",
            headers=self._headers(),
            json={"name": name, "description": description}
        )
        response.raise_for_status()
        return response.json()
    
    def ingest_git(
        self, 
        workspace_id: int, 
        name: str, 
        repo_url: str, 
        branch: str = "main"
    ) -> Dict[str, Any]:
        """Ingest a Git repository."""
        response = requests.post(
            f"{self.base_url}/api/ingestion/git",
            headers=self._headers(),
            json={
                "workspace_id": workspace_id,
                "name": name,
                "repo_url": repo_url,
                "branch": branch
            }
        )
        response.raise_for_status()
        return response.json()
    
    def query(
        self, 
        workspace_id: int, 
        question: str,
        rag_technique: str = "standard",
        k: int = 5
    ) -> Dict[str, Any]:
        """Query the knowledge base."""
        response = requests.post(
            f"{self.base_url}/api/query/",
            headers=self._headers(),
            json={
                "workspace_id": workspace_id,
                "question": question,
                "rag_technique": rag_technique,
                "k": k
            }
        )
        response.raise_for_status()
        return response.json()
    
    def chat(
        self,
        workspace_id: int,
        session_id: int,
        message: str,
        rag_technique: str = "standard"
    ) -> Dict[str, Any]:
        """Send a chat message with context."""
        response = requests.post(
            f"{self.base_url}/api/query/chat/message",
            headers=self._headers(),
            json={
                "workspace_id": workspace_id,
                "session_id": session_id,
                "message": message,
                "rag_technique": rag_technique
            }
        )
        response.raise_for_status()
        return response.json()


# Usage Example
if __name__ == "__main__":
    client = RAGClient()
    
    # Login
    client.login("developer@example.com", "password123")
    
    # Create workspace
    workspace = client.create_workspace("My Project", "Project documentation")
    print(f"Created workspace: {workspace['id']}")
    
    # Ingest Git repo
    result = client.ingest_git(
        workspace_id=workspace["id"],
        name="source-code",
        repo_url="https://github.com/myorg/myrepo.git"
    )
    print(f"Ingested {result['documents_processed']} documents")
    
    # Query
    answer = client.query(
        workspace_id=workspace["id"],
        question="How do I configure the database?",
        rag_technique="standard"
    )
    print(f"Answer: {answer['answer']}")
    print(f"Sources: {answer['sources']}")
```

### JavaScript/TypeScript Client

```typescript
interface LoginResponse {
  access_token: string;
  token_type: string;
}

interface Workspace {
  id: number;
  name: string;
  description: string;
  is_active: boolean;
  created_at: string;
}

interface QueryResponse {
  success: boolean;
  answer: string;
  sources: Array<{
    content: string;
    metadata: Record<string, any>;
  }>;
  technique: string;
}

class RAGClient {
  private baseUrl: string;
  private token: string | null = null;

  constructor(baseUrl: string = 'http://localhost/rag/api') {
    this.baseUrl = baseUrl;
  }

  async login(email: string, password: string): Promise<string> {
    const response = await fetch(`${this.baseUrl}/api/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password }),
    });

    if (!response.ok) {
      throw new Error(`Login failed: ${response.statusText}`);
    }

    const data: LoginResponse = await response.json();
    this.token = data.access_token;
    return this.token;
  }

  private getHeaders(): HeadersInit {
    if (!this.token) {
      throw new Error('Not logged in. Call login() first.');
    }
    return {
      'Authorization': `Bearer ${this.token}`,
      'Content-Type': 'application/json',
    };
  }

  async listWorkspaces(): Promise<Workspace[]> {
    const response = await fetch(`${this.baseUrl}/api/workspaces/`, {
      headers: this.getHeaders(),
    });
    return response.json();
  }

  async createWorkspace(name: string, description: string = ''): Promise<Workspace> {
    const response = await fetch(`${this.baseUrl}/api/workspaces/`, {
      method: 'POST',
      headers: this.getHeaders(),
      body: JSON.stringify({ name, description }),
    });
    return response.json();
  }

  async query(
    workspaceId: number,
    question: string,
    ragTechnique: string = 'standard',
    k: number = 5
  ): Promise<QueryResponse> {
    const response = await fetch(`${this.baseUrl}/api/query/`, {
      method: 'POST',
      headers: this.getHeaders(),
      body: JSON.stringify({
        workspace_id: workspaceId,
        question,
        rag_technique: ragTechnique,
        k,
      }),
    });
    return response.json();
  }
}

// Usage
async function main() {
  const client = new RAGClient();
  
  await client.login('developer@example.com', 'password123');
  
  const workspaces = await client.listWorkspaces();
  console.log('Workspaces:', workspaces);
  
  const answer = await client.query(
    workspaces[0].id,
    'How do I configure logging?'
  );
  console.log('Answer:', answer.answer);
}

main().catch(console.error);
```

### cURL Examples

```bash
# === Authentication ===

# Register
curl -X POST http://localhost/rag/api/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com", "username": "user", "password": "password123"}'

# Login
TOKEN=$(curl -s -X POST http://localhost/rag/api/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com", "password": "password123"}' \
  | jq -r '.access_token')

echo "Token: $TOKEN"

# === Workspaces ===

# List workspaces
curl -X GET http://localhost/rag/api/api/workspaces/ \
  -H "Authorization: Bearer $TOKEN"

# Create workspace
curl -X POST http://localhost/rag/api/api/workspaces/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name": "my-project", "description": "Project docs"}'

# === Ingestion ===

# Ingest Git repository
curl -X POST http://localhost/rag/api/api/ingestion/git \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "workspace_id": 1,
    "name": "source-code",
    "repo_url": "https://github.com/org/repo.git",
    "branch": "main"
  }'

# Ingest code directory
curl -X POST http://localhost/rag/api/api/ingestion/code/directory \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "workspace_id": 1,
    "directory": "/path/to/code",
    "recursive": true,
    "max_depth": 3,
    "include_headers": true
  }'

# Upload files
curl -X POST http://localhost/rag/api/api/ingestion/upload \
  -H "Authorization: Bearer $TOKEN" \
  -F "workspace_id=1" \
  -F "files=@document.pdf" \
  -F "files=@readme.md"

# === Queries ===

# Simple query
curl -X POST http://localhost/rag/api/api/query/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "workspace_id": 1,
    "question": "How do I configure the database?",
    "rag_technique": "standard",
    "k": 5
  }'

# Chat message
curl -X POST http://localhost/rag/api/api/query/chat/message \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "workspace_id": 1,
    "session_id": 1,
    "message": "What are the authentication options?",
    "rag_technique": "rag_fusion"
  }'

# === RAG Engine ===

# List available techniques
curl -X GET http://localhost/rag/api/api/rag/techniques \
  -H "Authorization: Bearer $TOKEN"

# Get current config
curl -X GET http://localhost/rag/api/api/rag/config \
  -H "Authorization: Bearer $TOKEN"

# Update config
curl -X PUT http://localhost/rag/api/api/rag/config \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "config": {
      "llm_model": "llama3.2:3b",
      "llm_temperature": 0.1,
      "top_k": 5,
      "rag_technique": "standard"
    }
  }'
```

---

## Webhooks & Events

### Ingestion Events

Monitor ingestion progress by polling the data source status:

```bash
# Check ingestion status
curl -X GET http://localhost/rag/api/api/ingestion/sources/1 \
  -H "Authorization: Bearer $TOKEN"

# Response includes:
{
  "id": 1,
  "name": "source-code",
  "source_type": "git",
  "status": "completed",  // pending, processing, completed, failed
  "documents_count": 45,
  "last_synced": "2024-01-15T10:30:00Z",
  "error_message": null
}
```

### Error Handling

All API errors follow this format:

```json
{
  "detail": "Error message describing what went wrong"
}
```

Common HTTP status codes:

| Code | Meaning | Action |
|------|---------|--------|
| 400 | Bad Request | Check request body format |
| 401 | Unauthorized | Token expired or invalid |
| 403 | Forbidden | No access to this resource |
| 404 | Not Found | Resource doesn't exist |
| 422 | Validation Error | Check field requirements |
| 500 | Server Error | Contact administrator |

---

## Best Practices

### For End Users

1. **Organize by Project**: Create separate workspaces for different projects
2. **Keep Sources Updated**: Re-ingest Git repos when code changes significantly
3. **Use Appropriate Techniques**: Match RAG technique to query complexity
4. **Verify Sources**: Always check cited sources for accuracy
5. **Iterate on Queries**: Refine questions based on initial answers

### For Integrators

1. **Handle Token Expiration**: Implement automatic re-login
2. **Implement Retries**: Add exponential backoff for failed requests
3. **Cache Responses**: Cache frequently asked questions
4. **Monitor Usage**: Track API calls and response times
5. **Validate Input**: Sanitize user input before sending to API

### Security Recommendations

1. **Secure Tokens**: Never expose tokens in client-side code
2. **Use HTTPS**: Always use HTTPS in production
3. **Rotate Secrets**: Regularly rotate JWT secrets
4. **Limit Access**: Use workspace permissions appropriately
5. **Audit Logs**: Monitor API access patterns

---

## Troubleshooting

### Common Issues

#### "401 Unauthorized"
- Token has expired → Login again
- Token not included in header → Add `Authorization: Bearer <token>`

#### "Workspace not found"
- Workspace ID doesn't exist → List workspaces first
- No access to workspace → Check membership

#### "Ingestion failed"
- Git URL inaccessible → Check URL and permissions
- File format not supported → Check supported formats
- Disk space full → Clear old data sources

#### "No relevant documents found"
- Knowledge base empty → Ingest documents first
- Query too specific → Broaden the question
- Wrong workspace → Check workspace ID

### Getting Help

- **API Docs**: http://localhost/rag/api/docs
- **Health Check**: http://localhost/rag/api/health/
- **Logs**: Check backend logs for detailed errors

---

## Related Documentation

- [ARCHITECTURE.md](./ARCHITECTURE.md) - System design and components
- [FEATURES.md](./FEATURES.md) - Detailed feature documentation
- [README.md](./README.md) - Quick start guide

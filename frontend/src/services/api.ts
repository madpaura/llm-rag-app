import axios from 'axios';

// API URL configuration
// When behind nginx at /rag/api, use relative path
// Otherwise use the environment variable or default to localhost:8000
const getApiBaseUrl = () => {
  // If REACT_APP_API_URL is set, use it
  if (process.env.REACT_APP_API_URL) {
    return process.env.REACT_APP_API_URL;
  }
  
  // Check if we're running under /rag/ui path (nginx proxy on port 8080)
  // Also check the port to detect nginx proxy
  const isNginxProxy = window.location.pathname.startsWith('/rag/ui') || 
                       window.location.port === '8080';
  
  if (isNginxProxy) {
    // Use relative path for nginx proxy - requests go to same origin
    return '/rag/api';
  }
  
  // Default for local development (React dev server on port 3000)
  return 'http://localhost:8000';
};

const API_BASE_URL = getApiBaseUrl();
console.log('[API] Base URL:', API_BASE_URL, 'Path:', window.location.pathname, 'Port:', window.location.port);

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor to add auth token
apiClient.interceptors.request.use((config) => {
  const token = localStorage.getItem('auth_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Response interceptor for error handling
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('auth_token');
      // Use PUBLIC_URL for correct redirect path when hosted under subpath
      const basePath = process.env.PUBLIC_URL || '';
      window.location.href = `${basePath}/login`;
    }
    return Promise.reject(error);
  }
);

// Types
export interface User {
  id: number;
  email: string;
  username: string;
  full_name?: string;
  is_active: boolean;
  is_admin: boolean;
}

export interface LoginResponse {
  access_token: string;
  token_type: string;
  user: User;
}

export interface Workspace {
  id: number;
  name: string;
  description?: string;
  is_active: boolean;
  created_at: string;
  member_count: number;
  role: string;
}

export interface DataSource {
  id: number;
  name: string;
  source_type: string;
  source_url?: string;
  status: string;
  last_ingested?: string;
  created_at: string;
}

export interface ChatSession {
  id: number;
  workspace_id: number;
  title: string;
  created_at: string;
  updated_at: string;
}

export interface ChatMessage {
  id: number;
  role: 'user' | 'assistant' | 'system';
  content: string;
  metadata?: any;
  created_at: string;
}

export type RAGTechnique = 'standard' | 'rag_fusion' | 'hyde' | 'multi_query';

export interface CitationSource {
  id: number;
  title: string;
  source: string;
  score: number;
  content_preview: string;
  document_id?: number;
  chunk_id?: number;
  start_line?: number;
  end_line?: number;
  page_number?: number;
  file_path?: string;
  repo_url?: string;
  page_url?: string;
}

export interface QueryResponse {
  success: boolean;
  answer: string;
  sources: CitationSource[];
  context_used: boolean;
  retrieved_docs_count: number;
  technique?: string;
}

export interface DocumentContent {
  id: number;
  title: string;
  file_path?: string;
  file_type?: string;
  content: string;
  lines: string[];
  total_lines: number;
  metadata?: any;
  created_at: string;
}

export interface ChunkLocation {
  chunk_id: number;
  document_id: number;
  document_title: string;
  file_path?: string;
  chunk_index: number;
  content: string;
  start_line: number;
  end_line: number;
  start_char: number;
  end_char: number;
  page_number?: number;
  metadata?: any;
}

export interface IngestionResponse {
  success: boolean;
  data_source_id: number;
  message: string;
  documents_count: number;
  error?: string;
}

export interface CodeIngestionStats {
  files_processed: number;
  functions_extracted: number;
  classes_extracted: number;
  structs_extracted: number;
  summaries_generated: number;
  embeddings_created: number;
  errors: string[];
}

export interface CodeIngestionResponse {
  success: boolean;
  data_source_id: number;
  message: string;
  stats: CodeIngestionStats;
}

export interface CodeUnit {
  id: number;
  unit_type: string;
  name: string;
  signature?: string;
  summary?: string;
  code?: string;
  start_line: number;
  end_line: number;
  language: string;
  parent_id?: number;
  calls?: Array<{ name: string; line: number; resolved: boolean }>;
  called_by?: Array<{ caller_id: number; line: number }>;
}

// API functions
export const api = {
  // Authentication
  async login(email: string, password: string): Promise<LoginResponse> {
    const response = await apiClient.post('/api/auth/login', { email, password });
    return response.data;
  },

  async register(email: string, username: string, password: string, full_name?: string): Promise<User> {
    const response = await apiClient.post('/api/auth/register', {
      email,
      username,
      password,
      full_name,
    });
    return response.data.user;
  },

  async getCurrentUser(token?: string): Promise<User> {
    const config = token ? { headers: { Authorization: `Bearer ${token}` } } : {};
    const response = await apiClient.get('/api/auth/me', config);
    return response.data;
  },

  async logout(): Promise<void> {
    await apiClient.post('/api/auth/logout');
  },

  // Workspaces
  async getWorkspaces(): Promise<Workspace[]> {
    const response = await apiClient.get('/api/workspaces/');
    return response.data;
  },

  async createWorkspace(name: string, description?: string): Promise<Workspace> {
    const response = await apiClient.post('/api/workspaces/', { name, description });
    return response.data;
  },

  async getWorkspace(workspaceId: number): Promise<Workspace> {
    const response = await apiClient.get(`/api/workspaces/${workspaceId}`);
    return response.data;
  },

  async getWorkspaceMembers(workspaceId: number): Promise<any[]> {
    const response = await apiClient.get(`/api/workspaces/${workspaceId}/members`);
    return response.data;
  },

  async deleteWorkspace(workspaceId: number): Promise<{ success: boolean; message: string }> {
    const response = await apiClient.delete(`/api/workspaces/${workspaceId}`);
    return response.data;
  },

  // Data Sources
  async getDataSources(workspaceId: number): Promise<DataSource[]> {
    const response = await apiClient.get(`/api/ingestion/sources/${workspaceId}`);
    return response.data;
  },

  async ingestGitRepository(data: {
    workspace_id: number;
    name: string;
    repo_url: string;
    branch?: string;
    username?: string;
    token?: string;
    language_filter?: string;
    max_depth?: number;
  }): Promise<IngestionResponse> {
    const response = await apiClient.post('/api/ingestion/git', data);
    return response.data;
  },

  async getIngestionProgress(dataSourceId: number): Promise<{
    data_source_id: number;
    status: string;
    in_progress: boolean;
    stage: string;
    stage_num: number;
    total_stages: number;
    current: number;
    total: number;
    percent: number;
    message: string;
  }> {
    const response = await apiClient.get(`/api/ingestion/progress/${dataSourceId}`);
    return response.data;
  },

  async ingestConfluenceSpace(data: {
    workspace_id: number;
    name: string;
    space_key: string;
    base_url?: string;
    username?: string;
    api_token?: string;
  }): Promise<IngestionResponse> {
    const response = await apiClient.post('/api/ingestion/confluence', data);
    return response.data;
  },

  async ingestDocument(
    workspaceId: number,
    name: string,
    file: File
  ): Promise<IngestionResponse> {
    const formData = new FormData();
    formData.append('workspace_id', workspaceId.toString());
    formData.append('name', name);
    formData.append('file', file);

    const response = await apiClient.post('/api/ingestion/document', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return response.data;
  },

  async getIngestionStatus(dataSourceId: number): Promise<DataSource> {
    const response = await apiClient.get(`/api/ingestion/status/${dataSourceId}`);
    return response.data;
  },

  async deleteDataSource(dataSourceId: number): Promise<void> {
    await apiClient.delete(`/api/ingestion/sources/${dataSourceId}`);
  },

  // Query and Chat
  async searchKnowledgeBase(
    question: string,
    workspaceId: number,
    k: number = 5,
    ragTechnique?: RAGTechnique
  ): Promise<QueryResponse> {
    const response = await apiClient.post('/api/query/search', {
      question,
      workspace_id: workspaceId,
      k,
      rag_technique: ragTechnique,
    });
    return response.data;
  },

  async createChatSession(workspaceId: number, title?: string): Promise<ChatSession> {
    const response = await apiClient.post('/api/query/chat/sessions', {
      workspace_id: workspaceId,
      title,
    });
    return response.data;
  },

  async getChatSessions(workspaceId: number): Promise<ChatSession[]> {
    const response = await apiClient.get(`/api/query/chat/sessions/${workspaceId}`);
    return response.data;
  },

  async sendChatMessage(
    sessionId: number, 
    message: string,
    ragTechnique?: RAGTechnique
  ): Promise<{
    success: boolean;
    message_id: number;
    answer: string;
    sources: any[];
    context_used: boolean;
    technique?: string;
  }> {
    const response = await apiClient.post('/api/query/chat/message', {
      session_id: sessionId,
      message,
      rag_technique: ragTechnique,
    });
    return response.data;
  },

  async getChatHistory(sessionId: number, limit: number = 50): Promise<{
    session_id: number;
    messages: ChatMessage[];
  }> {
    const response = await apiClient.get(`/api/query/chat/history/${sessionId}?limit=${limit}`);
    return response.data;
  },

  async deleteChatSession(sessionId: number): Promise<{ success: boolean; message: string }> {
    const response = await apiClient.delete(`/api/query/chat/sessions/${sessionId}`);
    return response.data;
  },

  // Health checks
  async healthCheck(): Promise<{ status: string; service: string; version: string }> {
    const response = await apiClient.get('/health/');
    return response.data;
  },

  // Document viewer
  async getDocument(documentId: number): Promise<DocumentContent> {
    const response = await apiClient.get(`/api/ingestion/documents/${documentId}`);
    return response.data;
  },

  async getDocumentChunk(documentId: number, chunkId: number): Promise<ChunkLocation> {
    const response = await apiClient.get(`/api/ingestion/documents/${documentId}/chunk/${chunkId}`);
    return response.data;
  },

  async getWorkspaceDocuments(workspaceId: number): Promise<Array<{
    id: number;
    title: string;
    file_path?: string;
    file_type?: string;
    created_at: string;
  }>> {
    const response = await apiClient.get(`/api/ingestion/documents/by-workspace/${workspaceId}`);
    return response.data;
  },

  // Code ingestion
  async ingestCodeFiles(
    workspaceId: number,
    name: string,
    files: File[]
  ): Promise<CodeIngestionResponse> {
    const formData = new FormData();
    formData.append('workspace_id', workspaceId.toString());
    formData.append('name', name);
    files.forEach(file => formData.append('files', file));

    const response = await apiClient.post('/api/ingestion/code', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    return response.data;
  },

  async ingestCodeDirectory(
    workspaceId: number,
    name: string,
    directoryPath: string,
    maxDepth?: number,
    includeHeaders: boolean = true
  ): Promise<CodeIngestionResponse> {
    const response = await apiClient.post('/api/ingestion/code/directory', {
      workspace_id: workspaceId,
      name,
      directory_path: directoryPath,
      max_depth: maxDepth,
      include_headers: includeHeaders,
    });
    return response.data;
  },

  async getCodeUnits(documentId: number): Promise<CodeUnit[]> {
    const response = await apiClient.get(`/api/ingestion/code/units/${documentId}`);
    return response.data;
  },

  async getCodeUnitDetail(unitId: number): Promise<CodeUnit> {
    const response = await apiClient.get(`/api/ingestion/code/units/${unitId}/detail`);
    return response.data;
  },

  async getCallGraph(workspaceId: number): Promise<{
    nodes: Array<{ id: number; name: string; type: string; file: string }>;
    edges: Array<{ source: number; target: number | null; target_name: string; resolved: boolean }>;
  }> {
    const response = await apiClient.get(`/api/ingestion/code/call-graph/${workspaceId}`);
    return response.data;
  },
};

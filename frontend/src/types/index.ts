// User and Authentication Types
export interface User {
  id: string;
  username: string;
  email: string;
  is_admin: boolean;
  created_at: string;
}

export interface LoginRequest {
  username: string;
  password: string;
}

export interface RegisterRequest {
  username: string;
  email: string;
  password: string;
}

export interface AuthResponse {
  success: boolean;
  message: string;
  user?: User;
  token?: string;
}

// Workspace Types
export interface Workspace {
  id: string;
  name: string;
  description: string;
  created_at: string;
  updated_at: string;
  member_count: number;
  data_source_count: number;
}

export interface WorkspaceMember {
  id: string;
  user_id: string;
  workspace_id: string;
  role: 'owner' | 'admin' | 'member';
  joined_at: string;
  user: User;
}

export interface CreateWorkspaceRequest {
  name: string;
  description: string;
}

// Data Source Types
export interface DataSource {
  id: string;
  workspace_id: string;
  name: string;
  type: 'git' | 'confluence' | 'document';
  status: 'pending' | 'processing' | 'completed' | 'failed';
  config: Record<string, any>;
  created_at: string;
  updated_at: string;
  document_count: number;
  chunk_count: number;
}

export interface GitIngestionRequest {
  workspace_id: string;
  repository_url: string;
  branch?: string;
  access_token?: string;
  include_patterns?: string[];
  exclude_patterns?: string[];
}

export interface ConfluenceIngestionRequest {
  workspace_id: string;
  base_url: string;
  space_key: string;
  username: string;
  api_token: string;
}

export interface DocumentUploadRequest {
  workspace_id: string;
  files: File[];
}

export interface IngestionStatus {
  id: string;
  status: 'pending' | 'processing' | 'completed' | 'failed';
  progress: number;
  message: string;
  documents_processed: number;
  chunks_created: number;
  error?: string;
}

// Chat Types
export interface ChatSession {
  id: string;
  workspace_id: string;
  name: string;
  created_at: string;
  updated_at: string;
  message_count: number;
}

export interface ChatMessage {
  id: string;
  session_id: string;
  role: 'user' | 'assistant';
  content: string;
  sources?: SourceReference[];
  created_at: string;
}

export interface SourceReference {
  document_id: string;
  document_name: string;
  chunk_id: string;
  content: string;
  similarity_score: number;
  metadata: Record<string, any>;
}

export interface ChatRequest {
  message: string;
  session_id?: string;
  workspace_id: string;
}

export interface ChatResponse {
  success: boolean;
  message: ChatMessage;
  session_id: string;
  sources: SourceReference[];
}

// Query Types
export interface SearchRequest {
  query: string;
  workspace_id: string;
  limit?: number;
  similarity_threshold?: number;
}

export interface SearchResult {
  document_id: string;
  document_name: string;
  chunk_id: string;
  content: string;
  similarity_score: number;
  metadata: Record<string, any>;
}

export interface SearchResponse {
  success: boolean;
  results: SearchResult[];
  query: string;
  total_results: number;
}

// API Response Types
export interface ApiResponse<T = any> {
  success: boolean;
  message?: string;
  data?: T;
  error?: string;
}

export interface PaginatedResponse<T> {
  success: boolean;
  data: T[];
  total: number;
  page: number;
  per_page: number;
  total_pages: number;
}

// UI Component Types
export interface LoadingState {
  isLoading: boolean;
  message?: string;
}

export interface ErrorState {
  hasError: boolean;
  message?: string;
  details?: string;
}

// WebSocket Types
export interface WebSocketMessage {
  type: 'chat_message' | 'status_update' | 'error';
  data: any;
  timestamp: string;
}

// Health Check Types
export interface HealthStatus {
  status: 'healthy' | 'unhealthy';
  database: boolean;
  vector_store: boolean;
  llm_service: boolean;
  timestamp: string;
}

// API Configuration
export const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';
export const WS_BASE_URL = process.env.REACT_APP_WS_URL || 'ws://localhost:8000';

// Authentication
export const AUTH_TOKEN_KEY = 'rag_auth_token';
export const USER_DATA_KEY = 'rag_user_data';

// Pagination
export const DEFAULT_PAGE_SIZE = 20;
export const MAX_PAGE_SIZE = 100;

// File Upload
export const MAX_FILE_SIZE = 10 * 1024 * 1024; // 10MB
export const ALLOWED_FILE_TYPES = [
  'application/pdf',
  'application/msword',
  'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
  'text/plain',
  'text/markdown',
];

// Chat
export const MAX_MESSAGE_LENGTH = 4000;
export const TYPING_INDICATOR_DELAY = 1000;

// Search
export const DEFAULT_SIMILARITY_THRESHOLD = 0.7;
export const MAX_SEARCH_RESULTS = 50;

// Workspace
export const MAX_WORKSPACE_NAME_LENGTH = 100;
export const MAX_WORKSPACE_DESCRIPTION_LENGTH = 500;

// Data Source Types
export const DATA_SOURCE_TYPES = {
  GIT: 'git',
  CONFLUENCE: 'confluence',
  DOCUMENT: 'document',
} as const;

export const DATA_SOURCE_STATUS = {
  PENDING: 'pending',
  PROCESSING: 'processing',
  COMPLETED: 'completed',
  FAILED: 'failed',
} as const;

// UI Constants
export const SIDEBAR_WIDTH = 280;
export const HEADER_HEIGHT = 64;
export const CHAT_INPUT_HEIGHT = 120;

// Timeouts
export const API_TIMEOUT = 30000; // 30 seconds
export const WEBSOCKET_RECONNECT_DELAY = 3000; // 3 seconds
export const DEBOUNCE_DELAY = 300; // 300ms

// Local Storage Keys
export const STORAGE_KEYS = {
  AUTH_TOKEN: AUTH_TOKEN_KEY,
  USER_DATA: USER_DATA_KEY,
  THEME: 'rag_theme',
  SIDEBAR_COLLAPSED: 'rag_sidebar_collapsed',
  RECENT_WORKSPACES: 'rag_recent_workspaces',
  CHAT_HISTORY: 'rag_chat_history',
} as const;

// Theme
export const THEMES = {
  LIGHT: 'light',
  DARK: 'dark',
  SYSTEM: 'system',
} as const;

// Error Messages
export const ERROR_MESSAGES = {
  NETWORK_ERROR: 'Network error. Please check your connection.',
  UNAUTHORIZED: 'You are not authorized to perform this action.',
  SERVER_ERROR: 'Server error. Please try again later.',
  VALIDATION_ERROR: 'Please check your input and try again.',
  FILE_TOO_LARGE: `File size must be less than ${MAX_FILE_SIZE / (1024 * 1024)}MB`,
  INVALID_FILE_TYPE: 'Invalid file type. Please upload a supported file.',
  REQUIRED_FIELD: 'This field is required.',
} as const;

// Success Messages
export const SUCCESS_MESSAGES = {
  LOGIN_SUCCESS: 'Successfully logged in!',
  LOGOUT_SUCCESS: 'Successfully logged out!',
  REGISTRATION_SUCCESS: 'Account created successfully!',
  WORKSPACE_CREATED: 'Workspace created successfully!',
  DATA_SOURCE_ADDED: 'Data source added successfully!',
  FILE_UPLOADED: 'File uploaded successfully!',
  SETTINGS_SAVED: 'Settings saved successfully!',
} as const;

// Routes
export const ROUTES = {
  HOME: '/',
  LOGIN: '/login',
  REGISTER: '/register',
  DASHBOARD: '/dashboard',
  WORKSPACE: '/workspace/:id',
  INGESTION: '/ingestion',
  SETTINGS: '/settings',
} as const;

// WebSocket Events
export const WS_EVENTS = {
  CONNECT: 'connect',
  DISCONNECT: 'disconnect',
  CHAT_MESSAGE: 'chat_message',
  TYPING_START: 'typing_start',
  TYPING_STOP: 'typing_stop',
  STATUS_UPDATE: 'status_update',
  ERROR: 'error',
} as const;

import React, { useState, useEffect, useMemo } from 'react';
import { useParams, Link, useNavigate } from 'react-router-dom';
import { MessageSquare, Upload, Database, Plus, Send, Loader2, Trash2, Search, X } from 'lucide-react';
import { api, Workspace, ChatSession, DataSource } from '../services/api';
import { ChatInterface } from '../components/ChatInterface';

export function WorkspaceView() {
  const { workspaceId } = useParams<{ workspaceId: string }>();
  const navigate = useNavigate();
  const [workspace, setWorkspace] = useState<Workspace | null>(null);
  const [chatSessions, setChatSessions] = useState<ChatSession[]>([]);
  const [dataSources, setDataSources] = useState<DataSource[]>([]);
  const [activeChatSession, setActiveChatSession] = useState<ChatSession | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [isDeleting, setIsDeleting] = useState(false);
  const [dataSourceSearch, setDataSourceSearch] = useState('');
  const [deletingSessionId, setDeletingSessionId] = useState<number | null>(null);
  const [deletingDataSourceId, setDeletingDataSourceId] = useState<number | null>(null);

  useEffect(() => {
    if (workspaceId) {
      loadWorkspaceData();
    }
  }, [workspaceId]);

  const loadWorkspaceData = async () => {
    try {
      setLoading(true);
      const wsId = parseInt(workspaceId!);
      
      const [workspaceData, sessionsData, sourcesData] = await Promise.all([
        api.getWorkspace(wsId),
        api.getChatSessions(wsId),
        api.getDataSources(wsId)
      ]);

      setWorkspace(workspaceData);
      setChatSessions(sessionsData);
      setDataSources(sourcesData);

      // Set the first session as active if available
      if (sessionsData.length > 0) {
        setActiveChatSession(sessionsData[0]);
      }
    } catch (err) {
      setError('Failed to load workspace data');
      console.error('Error loading workspace:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleCreateChatSession = async () => {
    if (!workspaceId) return;

    try {
      const title = prompt('Enter chat session title (optional):') || undefined;
      const newSession = await api.createChatSession(parseInt(workspaceId), title);
      setChatSessions([newSession, ...chatSessions]);
      setActiveChatSession(newSession);
    } catch (err) {
      alert('Failed to create chat session');
      console.error('Error creating chat session:', err);
    }
  };

  const handleDeleteWorkspace = async () => {
    if (!workspaceId || !workspace) return;

    const confirmed = window.confirm(
      `Are you sure you want to delete "${workspace.name}"?\n\nThis will permanently delete:\n- All chat sessions and messages\n- All data sources and documents\n- All workspace members\n\nThis action cannot be undone.`
    );

    if (!confirmed) return;

    try {
      setIsDeleting(true);
      await api.deleteWorkspace(parseInt(workspaceId));
      navigate('/');
    } catch (err) {
      alert('Failed to delete workspace');
      console.error('Error deleting workspace:', err);
      setIsDeleting(false);
    }
  };

  const handleDeleteChatSession = async (sessionId: number, e: React.MouseEvent) => {
    e.stopPropagation();
    
    const confirmed = window.confirm('Are you sure you want to delete this chat session? All messages will be lost.');
    if (!confirmed) return;

    try {
      setDeletingSessionId(sessionId);
      await api.deleteChatSession(sessionId);
      setChatSessions(chatSessions.filter(s => s.id !== sessionId));
      if (activeChatSession?.id === sessionId) {
        setActiveChatSession(chatSessions.find(s => s.id !== sessionId) || null);
      }
    } catch (err) {
      alert('Failed to delete chat session');
      console.error('Error deleting chat session:', err);
    } finally {
      setDeletingSessionId(null);
    }
  };

  const handleDeleteDataSource = async (dataSourceId: number, e: React.MouseEvent) => {
    e.stopPropagation();
    
    const confirmed = window.confirm('Are you sure you want to delete this data source? All associated documents will be removed.');
    if (!confirmed) return;

    try {
      setDeletingDataSourceId(dataSourceId);
      await api.deleteDataSource(dataSourceId);
      setDataSources(dataSources.filter(ds => ds.id !== dataSourceId));
    } catch (err) {
      alert('Failed to delete data source');
      console.error('Error deleting data source:', err);
    } finally {
      setDeletingDataSourceId(null);
    }
  };

  // Filter data sources based on search
  const filteredDataSources = useMemo(() => {
    if (!dataSourceSearch.trim()) return dataSources;
    const search = dataSourceSearch.toLowerCase();
    return dataSources.filter(ds => 
      ds.name.toLowerCase().includes(search) ||
      ds.source_type.toLowerCase().includes(search)
    );
  }, [dataSources, dataSourceSearch]);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600"></div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-center">
          <p className="text-red-600">{error}</p>
          <button
            onClick={loadWorkspaceData}
            className="mt-2 text-primary-600 hover:text-primary-500"
          >
            Try again
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="flex h-full">
      {/* Sidebar */}
      <div className="w-80 bg-white border-r border-gray-200 flex flex-col">
        {/* Workspace Header */}
        <div className="p-4 border-b border-gray-200">
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-semibold text-gray-900">{workspace?.name}</h2>
            <button
              onClick={handleDeleteWorkspace}
              disabled={isDeleting}
              className="p-1.5 text-gray-400 hover:text-red-600 hover:bg-red-50 rounded transition-colors disabled:opacity-50"
              title="Delete workspace"
            >
              {isDeleting ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Trash2 className="h-4 w-4" />
              )}
            </button>
          </div>
          {workspace?.description && (
            <p className="text-sm text-gray-500 mt-1">{workspace.description}</p>
          )}
        </div>

        {/* Data Sources */}
        <div className="p-4 border-b border-gray-200">
          <div className="flex items-center justify-between mb-3">
            <h3 className="text-sm font-medium text-gray-700">Data Sources</h3>
            <Link
              to={`/workspace/${workspaceId}/ingest`}
              className="p-1 text-gray-400 hover:text-gray-600 rounded"
              title="Add data source"
            >
              <Plus className="h-4 w-4" />
            </Link>
          </div>
          
          {/* Search box for data sources */}
          {dataSources.length > 3 && (
            <div className="relative mb-3">
              <Search className="absolute left-2 top-1/2 transform -translate-y-1/2 h-3 w-3 text-gray-400" />
              <input
                type="text"
                placeholder="Search sources..."
                value={dataSourceSearch}
                onChange={(e) => setDataSourceSearch(e.target.value)}
                className="w-full pl-7 pr-7 py-1.5 text-xs border border-gray-200 rounded focus:ring-1 focus:ring-primary-500 focus:border-primary-500"
              />
              {dataSourceSearch && (
                <button
                  onClick={() => setDataSourceSearch('')}
                  className="absolute right-2 top-1/2 transform -translate-y-1/2 text-gray-400 hover:text-gray-600"
                >
                  <X className="h-3 w-3" />
                </button>
              )}
            </div>
          )}
          
          {dataSources.length === 0 ? (
            <div className="text-center py-4">
              <Database className="mx-auto h-8 w-8 text-gray-400" />
              <p className="text-xs text-gray-500 mt-2">No data sources</p>
              <Link
                to={`/workspace/${workspaceId}/ingest`}
                className="text-xs text-primary-600 hover:text-primary-500 mt-1 inline-block"
              >
                Add your first source
              </Link>
            </div>
          ) : filteredDataSources.length === 0 ? (
            <p className="text-xs text-gray-500 text-center py-2">No matching sources</p>
          ) : (
            <div className="space-y-2 max-h-48 overflow-y-auto">
              {filteredDataSources.map((source) => (
                <div key={source.id} className="flex items-center space-x-2 p-2 bg-gray-50 rounded group">
                  <div className={`w-2 h-2 rounded-full flex-shrink-0 ${
                    source.status === 'completed' ? 'bg-green-500' :
                    source.status === 'processing' ? 'bg-yellow-500' :
                    source.status === 'failed' ? 'bg-red-500' : 'bg-gray-400'
                  }`} />
                  <div className="flex-1 min-w-0">
                    <p className="text-xs font-medium text-gray-900 truncate">{source.name}</p>
                    <p className="text-xs text-gray-500 capitalize">{source.source_type}</p>
                  </div>
                  <button
                    onClick={(e) => handleDeleteDataSource(source.id, e)}
                    disabled={deletingDataSourceId === source.id}
                    className="p-1 text-gray-400 hover:text-red-600 opacity-0 group-hover:opacity-100 transition-opacity disabled:opacity-50"
                    title="Delete data source"
                  >
                    {deletingDataSourceId === source.id ? (
                      <Loader2 className="h-3 w-3 animate-spin" />
                    ) : (
                      <Trash2 className="h-3 w-3" />
                    )}
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Chat Sessions */}
        <div className="flex-1 p-4">
          <div className="flex items-center justify-between mb-3">
            <h3 className="text-sm font-medium text-gray-700">Chat Sessions</h3>
            <button
              onClick={handleCreateChatSession}
              className="p-1 text-gray-400 hover:text-gray-600 rounded"
              title="New chat session"
            >
              <Plus className="h-4 w-4" />
            </button>
          </div>

          {chatSessions.length === 0 ? (
            <div className="text-center py-4">
              <MessageSquare className="mx-auto h-8 w-8 text-gray-400" />
              <p className="text-xs text-gray-500 mt-2">No chat sessions</p>
              <button
                onClick={handleCreateChatSession}
                className="text-xs text-primary-600 hover:text-primary-500 mt-1"
              >
                Start your first chat
              </button>
            </div>
          ) : (
            <div className="space-y-1 max-h-96 overflow-y-auto scrollbar-thin">
              {chatSessions.map((session) => (
                <div
                  key={session.id}
                  onClick={() => setActiveChatSession(session)}
                  className={`w-full text-left p-3 rounded-lg text-sm transition-colors cursor-pointer group flex items-start justify-between ${
                    activeChatSession?.id === session.id
                      ? 'bg-primary-100 text-primary-700'
                      : 'hover:bg-gray-50 text-gray-700'
                  }`}
                >
                  <div className="flex-1 min-w-0">
                    <p className="font-medium truncate">{session.title}</p>
                    <p className="text-xs text-gray-500 mt-1">
                      {new Date(session.updated_at).toLocaleDateString()}
                    </p>
                  </div>
                  <button
                    onClick={(e) => handleDeleteChatSession(session.id, e)}
                    disabled={deletingSessionId === session.id}
                    className="p-1 text-gray-400 hover:text-red-600 opacity-0 group-hover:opacity-100 transition-opacity disabled:opacity-50 ml-2"
                    title="Delete chat session"
                  >
                    {deletingSessionId === session.id ? (
                      <Loader2 className="h-3 w-3 animate-spin" />
                    ) : (
                      <Trash2 className="h-3 w-3" />
                    )}
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Main Chat Area */}
      <div className="flex-1 flex flex-col">
        {activeChatSession ? (
          <ChatInterface
            session={activeChatSession}
            workspaceId={parseInt(workspaceId!)}
          />
        ) : (
          <div className="flex-1 flex items-center justify-center">
            <div className="text-center">
              <MessageSquare className="mx-auto h-12 w-12 text-gray-400" />
              <h3 className="mt-4 text-lg font-medium text-gray-900">
                Welcome to {workspace?.name}
              </h3>
              <p className="mt-2 text-gray-500 max-w-sm">
                Start a conversation with your knowledge base. Create a new chat session to begin.
              </p>
              <button
                onClick={handleCreateChatSession}
                className="mt-6 inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-primary-600 hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500"
              >
                <Plus className="h-4 w-4 mr-2" />
                Start New Chat
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

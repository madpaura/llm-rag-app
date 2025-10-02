import React, { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import { MessageSquare, Upload, Database, Plus, Send, Loader2 } from 'lucide-react';
import { api, Workspace, ChatSession, DataSource } from '../services/api';
import { ChatInterface } from '../components/ChatInterface';

export function WorkspaceView() {
  const { workspaceId } = useParams<{ workspaceId: string }>();
  const [workspace, setWorkspace] = useState<Workspace | null>(null);
  const [chatSessions, setChatSessions] = useState<ChatSession[]>([]);
  const [dataSources, setDataSources] = useState<DataSource[]>([]);
  const [activeChatSession, setActiveChatSession] = useState<ChatSession | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

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
          <h2 className="text-lg font-semibold text-gray-900">{workspace?.name}</h2>
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
          ) : (
            <div className="space-y-2">
              {dataSources.slice(0, 5).map((source) => (
                <div key={source.id} className="flex items-center space-x-2 p-2 bg-gray-50 rounded">
                  <div className={`w-2 h-2 rounded-full ${
                    source.status === 'completed' ? 'bg-green-500' :
                    source.status === 'processing' ? 'bg-yellow-500' :
                    source.status === 'failed' ? 'bg-red-500' : 'bg-gray-400'
                  }`} />
                  <div className="flex-1 min-w-0">
                    <p className="text-xs font-medium text-gray-900 truncate">{source.name}</p>
                    <p className="text-xs text-gray-500 capitalize">{source.source_type}</p>
                  </div>
                </div>
              ))}
              {dataSources.length > 5 && (
                <p className="text-xs text-gray-500 text-center">
                  +{dataSources.length - 5} more sources
                </p>
              )}
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
                <button
                  key={session.id}
                  onClick={() => setActiveChatSession(session)}
                  className={`w-full text-left p-3 rounded-lg text-sm transition-colors ${
                    activeChatSession?.id === session.id
                      ? 'bg-primary-100 text-primary-700'
                      : 'hover:bg-gray-50 text-gray-700'
                  }`}
                >
                  <p className="font-medium truncate">{session.title}</p>
                  <p className="text-xs text-gray-500 mt-1">
                    {new Date(session.updated_at).toLocaleDateString()}
                  </p>
                </button>
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

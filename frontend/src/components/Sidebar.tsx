import React, { useState, useEffect } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { Home, FolderOpen, Upload, MessageSquare, Plus } from 'lucide-react';
import { api, Workspace } from '../services/api';
import { useAuth } from '../contexts/AuthContext';

export function Sidebar() {
  const location = useLocation();
  const { user } = useAuth();
  const [workspaces, setWorkspaces] = useState<Workspace[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadWorkspaces();
  }, []);

  const loadWorkspaces = async () => {
    try {
      const data = await api.getWorkspaces();
      setWorkspaces(data);
    } catch (error) {
      console.error('Failed to load workspaces:', error);
    } finally {
      setLoading(false);
    }
  };

  const isActive = (path: string) => {
    return location.pathname === path || location.pathname.startsWith(path);
  };

  return (
    <div className="w-64 bg-white border-r border-gray-200 flex flex-col">
      {/* Navigation */}
      <nav className="flex-1 px-4 py-6 space-y-2">
        <Link
          to="/dashboard"
          className={`flex items-center space-x-3 px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
            isActive('/dashboard')
              ? 'bg-primary-100 text-primary-700'
              : 'text-gray-700 hover:bg-gray-100'
          }`}
        >
          <Home className="h-5 w-5" />
          <span>Dashboard</span>
        </Link>

        {/* Workspaces Section */}
        <div className="pt-6">
          <div className="flex items-center justify-between px-3 mb-3">
            <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wider">
              Workspaces
            </h3>
            <button
              onClick={() => {
                const name = prompt('Enter workspace name:');
                if (name) {
                  api.createWorkspace(name).then(() => loadWorkspaces());
                }
              }}
              className="p-1 text-gray-400 hover:text-gray-600 rounded"
              title="Create workspace"
            >
              <Plus className="h-4 w-4" />
            </button>
          </div>

          {loading ? (
            <div className="px-3 py-2 text-sm text-gray-500">Loading...</div>
          ) : workspaces.length === 0 ? (
            <div className="px-3 py-2 text-sm text-gray-500">No workspaces</div>
          ) : (
            <div className="space-y-1">
              {workspaces.map((workspace) => (
                <div key={workspace.id} className="space-y-1">
                  <Link
                    to={`/workspace/${workspace.id}`}
                    className={`flex items-center space-x-3 px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
                      isActive(`/workspace/${workspace.id}`)
                        ? 'bg-primary-100 text-primary-700'
                        : 'text-gray-700 hover:bg-gray-100'
                    }`}
                  >
                    <FolderOpen className="h-4 w-4" />
                    <span className="truncate">{workspace.name}</span>
                  </Link>

                  {/* Workspace sub-navigation */}
                  {isActive(`/workspace/${workspace.id}`) && (
                    <div className="ml-7 space-y-1">
                      <Link
                        to={`/workspace/${workspace.id}/ingest`}
                        className={`flex items-center space-x-2 px-3 py-1 rounded text-xs transition-colors ${
                          isActive(`/workspace/${workspace.id}/ingest`)
                            ? 'bg-primary-50 text-primary-600'
                            : 'text-gray-600 hover:bg-gray-50'
                        }`}
                      >
                        <Upload className="h-3 w-3" />
                        <span>Ingest Data</span>
                      </Link>
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      </nav>

      {/* User info */}
      <div className="border-t border-gray-200 p-4">
        <div className="flex items-center space-x-3">
          <div className="w-8 h-8 bg-primary-500 rounded-full flex items-center justify-center">
            <span className="text-white text-sm font-medium">
              {user?.username?.charAt(0).toUpperCase()}
            </span>
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-sm font-medium text-gray-900 truncate">
              {user?.full_name || user?.username}
            </p>
            <p className="text-xs text-gray-500 truncate">{user?.email}</p>
          </div>
        </div>
      </div>
    </div>
  );
}

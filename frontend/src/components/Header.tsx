import React, { useState } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { LogOut, User, Link as LinkIcon, Plus, X } from 'lucide-react';

interface DocLink {
  id: string;
  name: string;
  url: string;
}

export function Header() {
  const { user, logout } = useAuth();
  const [docLinks, setDocLinks] = useState<DocLink[]>(() => {
    const saved = localStorage.getItem('doc_links');
    return saved ? JSON.parse(saved) : [];
  });
  const [showAddLink, setShowAddLink] = useState(false);
  const [newLink, setNewLink] = useState({ name: '', url: '' });

  const saveLinks = (links: DocLink[]) => {
    localStorage.setItem('doc_links', JSON.stringify(links));
    setDocLinks(links);
  };

  const handleAddLink = () => {
    if (newLink.name && newLink.url) {
      const link: DocLink = {
        id: Date.now().toString(),
        name: newLink.name,
        url: newLink.url.startsWith('http') ? newLink.url : `https://${newLink.url}`
      };
      saveLinks([...docLinks, link]);
      setNewLink({ name: '', url: '' });
      setShowAddLink(false);
    }
  };

  const handleRemoveLink = (id: string) => {
    saveLinks(docLinks.filter(link => link.id !== id));
  };

  return (
    <header className="bg-white border-b border-gray-200 px-6 py-4">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">RAG Assistant</h1>
          <p className="text-sm text-gray-500">AI-powered knowledge retrieval</p>
        </div>
        
        <div className="flex items-center space-x-4">
          {/* Doc Links */}
          <div className="flex items-center space-x-2">
            {docLinks.map((link) => (
              <div key={link.id} className="group relative">
                <a
                  href={link.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex items-center space-x-1 px-3 py-1.5 text-sm font-medium text-primary-600 hover:text-primary-700 bg-primary-50 hover:bg-primary-100 rounded-md transition-colors"
                >
                  <LinkIcon className="h-3.5 w-3.5" />
                  <span>{link.name}</span>
                </a>
                <button
                  onClick={() => handleRemoveLink(link.id)}
                  className="absolute -top-1 -right-1 hidden group-hover:flex items-center justify-center w-4 h-4 bg-red-500 text-white rounded-full text-xs hover:bg-red-600"
                  title="Remove link"
                >
                  <X className="h-3 w-3" />
                </button>
              </div>
            ))}
            
            {/* Add Link Button */}
            <div className="relative">
              <button
                onClick={() => setShowAddLink(!showAddLink)}
                className="flex items-center space-x-1 px-2 py-1.5 text-sm text-gray-500 hover:text-gray-700 hover:bg-gray-100 rounded-md transition-colors"
                title="Add documentation link"
              >
                <Plus className="h-4 w-4" />
                <LinkIcon className="h-3.5 w-3.5" />
              </button>
              
              {showAddLink && (
                <div className="absolute right-0 mt-2 w-72 bg-white border border-gray-200 rounded-lg shadow-lg z-20 p-4">
                  <h4 className="text-sm font-medium text-gray-900 mb-3">Add Documentation Link</h4>
                  <div className="space-y-3">
                    <div>
                      <label className="block text-xs font-medium text-gray-700 mb-1">Name</label>
                      <input
                        type="text"
                        value={newLink.name}
                        onChange={(e) => setNewLink({ ...newLink, name: e.target.value })}
                        placeholder="e.g., API Docs"
                        className="w-full px-3 py-1.5 text-sm border border-gray-300 rounded-md focus:ring-primary-500 focus:border-primary-500"
                      />
                    </div>
                    <div>
                      <label className="block text-xs font-medium text-gray-700 mb-1">URL</label>
                      <input
                        type="text"
                        value={newLink.url}
                        onChange={(e) => setNewLink({ ...newLink, url: e.target.value })}
                        placeholder="https://docs.example.com"
                        className="w-full px-3 py-1.5 text-sm border border-gray-300 rounded-md focus:ring-primary-500 focus:border-primary-500"
                      />
                    </div>
                    <div className="flex justify-end space-x-2">
                      <button
                        onClick={() => setShowAddLink(false)}
                        className="px-3 py-1.5 text-sm text-gray-600 hover:text-gray-800"
                      >
                        Cancel
                      </button>
                      <button
                        onClick={handleAddLink}
                        disabled={!newLink.name || !newLink.url}
                        className="px-3 py-1.5 text-sm bg-primary-600 text-white rounded-md hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed"
                      >
                        Add Link
                      </button>
                    </div>
                  </div>
                </div>
              )}
            </div>
          </div>

          <div className="h-6 w-px bg-gray-200" />
          
          <div className="flex items-center space-x-2">
            <User className="h-5 w-5 text-gray-400" />
            <span className="text-sm font-medium text-gray-700">
              {user?.full_name || user?.username}
            </span>
          </div>
          
          <button
            onClick={logout}
            className="flex items-center space-x-2 px-3 py-2 text-sm font-medium text-gray-700 hover:text-gray-900 hover:bg-gray-100 rounded-md transition-colors"
          >
            <LogOut className="h-4 w-4" />
            <span>Logout</span>
          </button>
        </div>
      </div>
    </header>
  );
}

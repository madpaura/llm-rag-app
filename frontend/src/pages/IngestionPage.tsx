import React, { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import { ArrowLeft, GitBranch, Globe, Upload, Loader2, CheckCircle, XCircle, Clock, Code, FileCode } from 'lucide-react';
import { api, DataSource, Workspace, CodeIngestionStats } from '../services/api';

export function IngestionPage() {
  const { workspaceId } = useParams<{ workspaceId: string }>();
  const [workspace, setWorkspace] = useState<Workspace | null>(null);
  const [dataSources, setDataSources] = useState<DataSource[]>([]);
  const [activeTab, setActiveTab] = useState<'git' | 'confluence' | 'document' | 'code'>('git');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  // Git form state
  const [gitForm, setGitForm] = useState({
    name: '',
    repo_url: '',
    branch: 'main',
    username: '',
    token: ''
  });

  // Confluence form state
  const [confluenceForm, setConfluenceForm] = useState({
    name: '',
    space_key: '',
    base_url: '',
    username: '',
    api_token: ''
  });

  // Document form state
  const [documentForm, setDocumentForm] = useState({
    name: '',
    files: [] as File[]
  });
  const [uploadProgress, setUploadProgress] = useState<{ current: number; total: number } | null>(null);

  // Code form state
  const [codeForm, setCodeForm] = useState({
    name: '',
    files: [] as File[],
    directoryPath: ''
  });
  const [codeStats, setCodeStats] = useState<CodeIngestionStats | null>(null);

  useEffect(() => {
    if (workspaceId) {
      loadWorkspaceData();
    }
  }, [workspaceId]);

  const loadWorkspaceData = async () => {
    try {
      const wsId = parseInt(workspaceId!);
      const [workspaceData, sourcesData] = await Promise.all([
        api.getWorkspace(wsId),
        api.getDataSources(wsId)
      ]);
      setWorkspace(workspaceData);
      setDataSources(sourcesData);
    } catch (err) {
      console.error('Error loading workspace data:', err);
    }
  };

  const handleGitSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!workspaceId) return;

    setLoading(true);
    setError('');
    setSuccess('');

    try {
      const result = await api.ingestGitRepository({
        workspace_id: parseInt(workspaceId),
        ...gitForm
      });

      if (result.success) {
        setSuccess(`Successfully ingested ${result.documents_count} documents from Git repository`);
        setGitForm({ name: '', repo_url: '', branch: 'main', username: '', token: '' });
        loadWorkspaceData();
      } else {
        setError(result.error || 'Failed to ingest Git repository');
      }
    } catch (err) {
      setError('Failed to ingest Git repository');
      console.error('Git ingestion error:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleConfluenceSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!workspaceId) return;

    setLoading(true);
    setError('');
    setSuccess('');

    try {
      const result = await api.ingestConfluenceSpace({
        workspace_id: parseInt(workspaceId),
        ...confluenceForm
      });

      if (result.success) {
        setSuccess(`Successfully ingested ${result.documents_count} documents from Confluence space`);
        setConfluenceForm({ name: '', space_key: '', base_url: '', username: '', api_token: '' });
        loadWorkspaceData();
      } else {
        setError(result.error || 'Failed to ingest Confluence space');
      }
    } catch (err) {
      setError('Failed to ingest Confluence space');
      console.error('Confluence ingestion error:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleDocumentSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!workspaceId || documentForm.files.length === 0) return;

    setLoading(true);
    setError('');
    setSuccess('');
    setUploadProgress({ current: 0, total: documentForm.files.length });

    const results: { success: number; failed: number; totalChunks: number } = {
      success: 0,
      failed: 0,
      totalChunks: 0
    };

    try {
      for (let i = 0; i < documentForm.files.length; i++) {
        const file = documentForm.files[i];
        setUploadProgress({ current: i + 1, total: documentForm.files.length });
        
        try {
          const name = documentForm.name 
            ? (documentForm.files.length > 1 ? `${documentForm.name} - ${file.name}` : documentForm.name)
            : file.name.replace(/\.[^/.]+$/, '');
          
          const result = await api.ingestDocument(
            parseInt(workspaceId),
            name,
            file
          );

          if (result.success) {
            results.success++;
            results.totalChunks += result.documents_count;
          } else {
            results.failed++;
          }
        } catch (err) {
          results.failed++;
          console.error(`Error ingesting ${file.name}:`, err);
        }
      }

      if (results.success > 0) {
        setSuccess(`Successfully ingested ${results.success} file(s) with ${results.totalChunks} total chunks${results.failed > 0 ? `. ${results.failed} file(s) failed.` : ''}`);
      } else {
        setError('Failed to ingest all documents');
      }
      
      setDocumentForm({ name: '', files: [] });
      loadWorkspaceData();
    } catch (err) {
      setError('Failed to ingest documents');
      console.error('Document ingestion error:', err);
    } finally {
      setLoading(false);
      setUploadProgress(null);
    }
  };

  const handleCodeSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!workspaceId || codeForm.files.length === 0) return;

    setLoading(true);
    setError('');
    setSuccess('');
    setCodeStats(null);

    try {
      const result = await api.ingestCodeFiles(
        parseInt(workspaceId),
        codeForm.name || 'Code Files',
        codeForm.files
      );

      if (result.success) {
        setCodeStats(result.stats);
        setSuccess(`Successfully processed ${result.stats.files_processed} files: ${result.stats.functions_extracted} functions, ${result.stats.classes_extracted} classes, ${result.stats.structs_extracted} structs`);
        setCodeForm({ name: '', files: [], directoryPath: '' });
        loadWorkspaceData();
      } else {
        setError('Failed to ingest code files');
      }
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to ingest code files');
      console.error('Code ingestion error:', err);
    } finally {
      setLoading(false);
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'completed':
        return <CheckCircle className="h-5 w-5 text-green-500" />;
      case 'processing':
        return <Clock className="h-5 w-5 text-yellow-500" />;
      case 'failed':
        return <XCircle className="h-5 w-5 text-red-500" />;
      default:
        return <Clock className="h-5 w-5 text-gray-400" />;
    }
  };

  return (
    <div className="p-6">
      {/* Header */}
      <div className="mb-6">
        <div className="flex items-center space-x-4 mb-4">
          <Link
            to={`/workspace/${workspaceId}`}
            className="p-2 text-gray-400 hover:text-gray-600 rounded-lg hover:bg-gray-100"
          >
            <ArrowLeft className="h-5 w-5" />
          </Link>
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Data Ingestion</h1>
            <p className="text-gray-600">Add data sources to {workspace?.name}</p>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Ingestion Forms */}
        <div className="lg:col-span-2">
          {/* Tabs */}
          <div className="border-b border-gray-200 mb-6">
            <nav className="-mb-px flex space-x-8">
              <button
                onClick={() => setActiveTab('git')}
                className={`py-2 px-1 border-b-2 font-medium text-sm ${
                  activeTab === 'git'
                    ? 'border-primary-500 text-primary-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                }`}
              >
                <GitBranch className="h-4 w-4 inline mr-2" />
                Git Repository
              </button>
              <button
                onClick={() => setActiveTab('confluence')}
                className={`py-2 px-1 border-b-2 font-medium text-sm ${
                  activeTab === 'confluence'
                    ? 'border-primary-500 text-primary-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                }`}
              >
                <Globe className="h-4 w-4 inline mr-2" />
                Confluence
              </button>
              <button
                onClick={() => setActiveTab('document')}
                className={`py-2 px-1 border-b-2 font-medium text-sm ${
                  activeTab === 'document'
                    ? 'border-primary-500 text-primary-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                }`}
              >
                <Upload className="h-4 w-4 inline mr-2" />
                Documents
              </button>
              <button
                onClick={() => setActiveTab('code')}
                className={`py-2 px-1 border-b-2 font-medium text-sm ${
                  activeTab === 'code'
                    ? 'border-primary-500 text-primary-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                }`}
              >
                <Code className="h-4 w-4 inline mr-2" />
                C/C++ Code
              </button>
            </nav>
          </div>

          {/* Status Messages */}
          {error && (
            <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-md">
              <p className="text-sm text-red-600">{error}</p>
            </div>
          )}

          {success && (
            <div className="mb-6 p-4 bg-green-50 border border-green-200 rounded-md">
              <p className="text-sm text-green-600">{success}</p>
            </div>
          )}

          {/* Git Repository Form */}
          {activeTab === 'git' && (
            <div className="bg-white rounded-lg shadow p-6">
              <h3 className="text-lg font-medium text-gray-900 mb-4">Ingest Git Repository</h3>
              <form onSubmit={handleGitSubmit} className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Name
                  </label>
                  <input
                    type="text"
                    required
                    value={gitForm.name}
                    onChange={(e) => setGitForm({ ...gitForm, name: e.target.value })}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-primary-500 focus:border-primary-500"
                    placeholder="My Project Repository"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Repository URL
                  </label>
                  <input
                    type="url"
                    required
                    value={gitForm.repo_url}
                    onChange={(e) => setGitForm({ ...gitForm, repo_url: e.target.value })}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-primary-500 focus:border-primary-500"
                    placeholder="https://github.com/user/repo.git"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Branch
                  </label>
                  <input
                    type="text"
                    value={gitForm.branch}
                    onChange={(e) => setGitForm({ ...gitForm, branch: e.target.value })}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-primary-500 focus:border-primary-500"
                    placeholder="main"
                  />
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Username (optional)
                    </label>
                    <input
                      type="text"
                      value={gitForm.username}
                      onChange={(e) => setGitForm({ ...gitForm, username: e.target.value })}
                      className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-primary-500 focus:border-primary-500"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Token (optional)
                    </label>
                    <input
                      type="password"
                      value={gitForm.token}
                      onChange={(e) => setGitForm({ ...gitForm, token: e.target.value })}
                      className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-primary-500 focus:border-primary-500"
                    />
                  </div>
                </div>

                <button
                  type="submit"
                  disabled={loading}
                  className="w-full flex items-center justify-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-primary-600 hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500 disabled:opacity-50"
                >
                  {loading ? (
                    <Loader2 className="h-4 w-4 animate-spin mr-2" />
                  ) : (
                    <GitBranch className="h-4 w-4 mr-2" />
                  )}
                  Ingest Repository
                </button>
              </form>
            </div>
          )}

          {/* Confluence Form */}
          {activeTab === 'confluence' && (
            <div className="bg-white rounded-lg shadow p-6">
              <h3 className="text-lg font-medium text-gray-900 mb-4">Ingest Confluence Space</h3>
              <form onSubmit={handleConfluenceSubmit} className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Name
                  </label>
                  <input
                    type="text"
                    required
                    value={confluenceForm.name}
                    onChange={(e) => setConfluenceForm({ ...confluenceForm, name: e.target.value })}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-primary-500 focus:border-primary-500"
                    placeholder="Project Documentation"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Space Key
                  </label>
                  <input
                    type="text"
                    required
                    value={confluenceForm.space_key}
                    onChange={(e) => setConfluenceForm({ ...confluenceForm, space_key: e.target.value })}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-primary-500 focus:border-primary-500"
                    placeholder="PROJ"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Base URL
                  </label>
                  <input
                    type="url"
                    value={confluenceForm.base_url}
                    onChange={(e) => setConfluenceForm({ ...confluenceForm, base_url: e.target.value })}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-primary-500 focus:border-primary-500"
                    placeholder="https://company.atlassian.net/wiki"
                  />
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Username
                    </label>
                    <input
                      type="text"
                      value={confluenceForm.username}
                      onChange={(e) => setConfluenceForm({ ...confluenceForm, username: e.target.value })}
                      className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-primary-500 focus:border-primary-500"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      API Token
                    </label>
                    <input
                      type="password"
                      value={confluenceForm.api_token}
                      onChange={(e) => setConfluenceForm({ ...confluenceForm, api_token: e.target.value })}
                      className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-primary-500 focus:border-primary-500"
                    />
                  </div>
                </div>

                <button
                  type="submit"
                  disabled={loading}
                  className="w-full flex items-center justify-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-primary-600 hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500 disabled:opacity-50"
                >
                  {loading ? (
                    <Loader2 className="h-4 w-4 animate-spin mr-2" />
                  ) : (
                    <Globe className="h-4 w-4 mr-2" />
                  )}
                  Ingest Space
                </button>
              </form>
            </div>
          )}

          {/* Document Form */}
          {activeTab === 'document' && (
            <div className="bg-white rounded-lg shadow p-6">
              <h3 className="text-lg font-medium text-gray-900 mb-4">Upload Documents</h3>
              <form onSubmit={handleDocumentSubmit} className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Name (optional)
                  </label>
                  <input
                    type="text"
                    value={documentForm.name}
                    onChange={(e) => setDocumentForm({ ...documentForm, name: e.target.value })}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-primary-500 focus:border-primary-500"
                    placeholder="Leave empty to use file names"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Files
                  </label>
                  <input
                    type="file"
                    required
                    multiple
                    accept=".pdf,.docx,.doc,.txt,.md"
                    onChange={(e) => setDocumentForm({ ...documentForm, files: Array.from(e.target.files || []) })}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-primary-500 focus:border-primary-500"
                  />
                  <p className="text-xs text-gray-500 mt-1">
                    Supported formats: PDF, Word (.docx, .doc), Text (.txt), Markdown (.md). Select multiple files.
                  </p>
                </div>

                {documentForm.files.length > 0 && (
                  <div className="bg-gray-50 rounded-md p-3">
                    <p className="text-sm font-medium text-gray-700 mb-2">
                      Selected files ({documentForm.files.length}):
                    </p>
                    <ul className="text-xs text-gray-600 space-y-1 max-h-32 overflow-y-auto">
                      {documentForm.files.map((file, index) => (
                        <li key={index} className="truncate">• {file.name}</li>
                      ))}
                    </ul>
                  </div>
                )}

                {uploadProgress && (
                  <div className="bg-blue-50 rounded-md p-3">
                    <p className="text-sm text-blue-700">
                      Uploading file {uploadProgress.current} of {uploadProgress.total}...
                    </p>
                    <div className="mt-2 w-full bg-blue-200 rounded-full h-2">
                      <div 
                        className="bg-blue-600 h-2 rounded-full transition-all duration-300"
                        style={{ width: `${(uploadProgress.current / uploadProgress.total) * 100}%` }}
                      />
                    </div>
                  </div>
                )}

                <button
                  type="submit"
                  disabled={loading || documentForm.files.length === 0}
                  className="w-full flex items-center justify-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-primary-600 hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500 disabled:opacity-50"
                >
                  {loading ? (
                    <Loader2 className="h-4 w-4 animate-spin mr-2" />
                  ) : (
                    <Upload className="h-4 w-4 mr-2" />
                  )}
                  Upload {documentForm.files.length > 1 ? `${documentForm.files.length} Documents` : 'Document'}
                </button>
              </form>
            </div>
          )}

          {/* C/C++ Code Form */}
          {activeTab === 'code' && (
            <div className="bg-white rounded-lg shadow p-6">
              <h3 className="text-lg font-medium text-gray-900 mb-4">Ingest C/C++ Source Code</h3>
              <p className="text-sm text-gray-600 mb-4">
                Upload C/C++ source files for AST-based parsing. Functions, classes, and structs will be 
                extracted and summarized using AI. Embeddings are created at function/class/file level.
              </p>
              
              <form onSubmit={handleCodeSubmit} className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Name
                  </label>
                  <input
                    type="text"
                    value={codeForm.name}
                    onChange={(e) => setCodeForm({ ...codeForm, name: e.target.value })}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-primary-500 focus:border-primary-500"
                    placeholder="My C++ Project"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Source Files
                  </label>
                  <input
                    type="file"
                    required
                    multiple
                    accept=".c,.h,.cpp,.cc,.cxx,.hpp,.hxx,.hh"
                    onChange={(e) => setCodeForm({ ...codeForm, files: Array.from(e.target.files || []) })}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-primary-500 focus:border-primary-500"
                  />
                  <p className="text-xs text-gray-500 mt-1">
                    Supported: .c, .h, .cpp, .cc, .cxx, .hpp, .hxx, .hh
                  </p>
                </div>

                {codeForm.files.length > 0 && (
                  <div className="bg-gray-50 rounded-md p-3">
                    <p className="text-sm font-medium text-gray-700 mb-2">
                      Selected files ({codeForm.files.length}):
                    </p>
                    <ul className="text-xs text-gray-600 space-y-1 max-h-32 overflow-y-auto">
                      {codeForm.files.map((file, index) => (
                        <li key={index} className="flex items-center truncate">
                          <FileCode className="h-3 w-3 mr-1 text-gray-400" />
                          {file.name}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}

                {codeStats && (
                  <div className="bg-green-50 rounded-md p-4">
                    <p className="text-sm font-medium text-green-800 mb-2">Ingestion Results:</p>
                    <div className="grid grid-cols-2 gap-2 text-xs text-green-700">
                      <div>Files processed: <span className="font-medium">{codeStats.files_processed}</span></div>
                      <div>Functions: <span className="font-medium">{codeStats.functions_extracted}</span></div>
                      <div>Classes: <span className="font-medium">{codeStats.classes_extracted}</span></div>
                      <div>Structs: <span className="font-medium">{codeStats.structs_extracted}</span></div>
                      <div>Summaries: <span className="font-medium">{codeStats.summaries_generated}</span></div>
                      <div>Embeddings: <span className="font-medium">{codeStats.embeddings_created}</span></div>
                    </div>
                    {codeStats.errors.length > 0 && (
                      <div className="mt-2 text-xs text-red-600">
                        Errors: {codeStats.errors.join(', ')}
                      </div>
                    )}
                  </div>
                )}

                <button
                  type="submit"
                  disabled={loading || codeForm.files.length === 0}
                  className="w-full flex items-center justify-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-primary-600 hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500 disabled:opacity-50"
                >
                  {loading ? (
                    <>
                      <Loader2 className="h-4 w-4 animate-spin mr-2" />
                      Processing (this may take a while)...
                    </>
                  ) : (
                    <>
                      <Code className="h-4 w-4 mr-2" />
                      Ingest {codeForm.files.length} Code File{codeForm.files.length !== 1 ? 's' : ''}
                    </>
                  )}
                </button>
              </form>

              <div className="mt-6 p-4 bg-blue-50 rounded-md">
                <h4 className="text-sm font-medium text-blue-800 mb-2">What happens during code ingestion:</h4>
                <ul className="text-xs text-blue-700 space-y-1">
                  <li>• <strong>AST Parsing:</strong> tree-sitter extracts functions, classes, structs</li>
                  <li>• <strong>Summary Generation:</strong> LLM generates descriptions for each code unit</li>
                  <li>• <strong>Hierarchical Processing:</strong> Function → Class → File summaries</li>
                  <li>• <strong>Call Graph:</strong> Function call relationships are tracked</li>
                  <li>• <strong>Embeddings:</strong> Code + summary combined for semantic search</li>
                </ul>
              </div>
            </div>
          )}
        </div>

        {/* Data Sources List */}
        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-lg font-medium text-gray-900 mb-4">Data Sources</h3>
          
          {dataSources.length === 0 ? (
            <p className="text-gray-500 text-sm">No data sources yet</p>
          ) : (
            <div className="space-y-3">
              {dataSources.map((source) => (
                <div key={source.id} className="flex items-center space-x-3 p-3 bg-gray-50 rounded-lg">
                  {getStatusIcon(source.status)}
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-gray-900 truncate">
                      {source.name}
                    </p>
                    <p className="text-xs text-gray-500 capitalize">
                      {source.source_type}
                    </p>
                    {source.last_ingested && (
                      <p className="text-xs text-gray-400">
                        Last: {new Date(source.last_ingested).toLocaleDateString()}
                      </p>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

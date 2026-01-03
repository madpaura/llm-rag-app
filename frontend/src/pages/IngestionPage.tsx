import React, { useState, useEffect, useRef } from 'react';
import { useParams, Link } from 'react-router-dom';
import { ArrowLeft, GitBranch, Globe, Upload, Loader2, CheckCircle, XCircle, Clock, Code, FileCode, Ticket, RotateCcw, X } from 'lucide-react';
import { api, DataSource, Workspace, CodeIngestionStats } from '../services/api';
import { useFormCache } from '../hooks/useFormCache';

// Progress tracking interface
interface IngestionProgress {
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
}

export function IngestionPage() {
  const { workspaceId } = useParams<{ workspaceId: string }>();
  const [workspace, setWorkspace] = useState<Workspace | null>(null);
  const [dataSources, setDataSources] = useState<DataSource[]>([]);
  const [activeTab, setActiveTab] = useState<'git' | 'confluence' | 'jira' | 'document' | 'code'>('git');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  
  // Progress tracking state
  const [ingestionProgress, setIngestionProgress] = useState<IngestionProgress | null>(null);
  const [activeDataSourceId, setActiveDataSourceId] = useState<number | null>(null);
  const progressIntervalRef = useRef<NodeJS.Timeout | null>(null);

  // Git form state with caching (token excluded from cache)
  const [gitForm, setGitForm, clearGitCache] = useFormCache('git_ingestion', {
    name: '',
    repo_url: '',
    branch: 'main',
    username: '',
    token: '',
    language_filter: 'all',
    max_depth: '' as string | number
  }, ['token']);

  // Language filter options
  const LANGUAGE_OPTIONS = [
    { value: 'all', label: 'All Languages', description: 'Python, JS, Java, C/C++, Go, Rust, Docs' },
    { value: 'c_cpp', label: 'C/C++', description: '.c, .h, .cpp, .hpp, .cc, .cxx' },
    { value: 'python', label: 'Python', description: '.py, .pyi, .pyx' },
    { value: 'javascript', label: 'JavaScript/TypeScript', description: '.js, .jsx, .ts, .tsx' },
    { value: 'java', label: 'Java', description: '.java' },
    { value: 'go', label: 'Go', description: '.go' },
    { value: 'rust', label: 'Rust', description: '.rs' },
    { value: 'docs', label: 'Documentation Only', description: '.md, .txt, .rst' },
  ];

  // Confluence form state with caching (api_token excluded from cache)
  const [confluenceForm, setConfluenceForm, clearConfluenceCache] = useFormCache('confluence_ingestion', {
    name: '',
    space_key: '',
    base_url: '',
    username: '',
    api_token: '',
    page_ids: '',
    max_depth: '' as string | number,
    include_children: true
  }, ['api_token']);

  // JIRA form state with caching (api_token excluded from cache)
  const [jiraForm, setJiraForm, clearJiraCache] = useFormCache('jira_ingestion', {
    name: '',
    project_key: '',
    base_url: '',
    username: '',
    api_token: '',
    issue_types: [] as string[],
    specific_tickets: '',
    max_results: '' as string | number
  }, ['api_token']);

  // JIRA issue type options
  const JIRA_ISSUE_TYPES = [
    { value: 'Story', label: 'Story' },
    { value: 'Epic', label: 'Epic' },
    { value: 'Bug', label: 'Bug' },
    { value: 'Task', label: 'Task' },
    { value: 'Sub-task', label: 'Sub-task' },
    { value: 'Improvement', label: 'Improvement' },
  ];

  // Document form state
  const [documentForm, setDocumentForm] = useState({
    name: '',
    files: [] as File[]
  });
  const [uploadProgress, setUploadProgress] = useState<{ current: number; total: number } | null>(null);

  // Code form state with caching (files excluded automatically)
  const [codeForm, setCodeForm, clearCodeCache] = useFormCache('code_ingestion', {
    name: '',
    files: [] as File[],
    directoryPath: '',
    maxDepth: '' as string | number,
    includeHeaders: true
  }, []);
  const [codeStats, setCodeStats] = useState<CodeIngestionStats | null>(null);

  useEffect(() => {
    if (workspaceId) {
      loadWorkspaceData();
      // Check for active ingestions when page loads
      checkActiveIngestions();
    }
    
    // Cleanup progress polling on unmount
    return () => {
      if (progressIntervalRef.current) {
        clearInterval(progressIntervalRef.current);
      }
    };
  }, [workspaceId]);

  // Check for active ingestions and resume progress tracking
  const checkActiveIngestions = async () => {
    try {
      const wsId = parseInt(workspaceId!);
      const activeIngestions = await api.getActiveIngestions(wsId);
      
      if (activeIngestions.length > 0) {
        // Resume tracking the first active ingestion
        const active = activeIngestions[0];
        setLoading(true);
        if (active.progress) {
          setIngestionProgress({
            data_source_id: active.data_source_id,
            status: active.status,
            in_progress: active.in_progress,
            ...active.progress
          });
        }
        startProgressPolling(active.data_source_id);
      }
    } catch (err) {
      console.error('Error checking active ingestions:', err);
    }
  };

  // Cancel ingestion
  const handleCancelIngestion = async () => {
    if (!activeDataSourceId) return;
    
    try {
      await api.cancelIngestion(activeDataSourceId);
      stopProgressPolling();
      setLoading(false);
      setSuccess('Ingestion cancelled');
      loadWorkspaceData();
    } catch (err) {
      console.error('Error cancelling ingestion:', err);
      setError('Failed to cancel ingestion');
    }
  };

  // Start polling for progress
  const startProgressPolling = (dataSourceId: number) => {
    setActiveDataSourceId(dataSourceId);
    
    // Clear any existing interval
    if (progressIntervalRef.current) {
      clearInterval(progressIntervalRef.current);
    }
    
    // Poll every 1 second
    progressIntervalRef.current = setInterval(async () => {
      try {
        const progress = await api.getIngestionProgress(dataSourceId);
        setIngestionProgress(progress);
        
        // Stop polling if no longer in progress
        if (!progress.in_progress || progress.status === 'completed' || progress.status === 'failed') {
          if (progressIntervalRef.current) {
            clearInterval(progressIntervalRef.current);
            progressIntervalRef.current = null;
          }
        }
      } catch (err) {
        console.error('Error fetching progress:', err);
      }
    }, 1000);
  };

  // Stop polling
  const stopProgressPolling = () => {
    if (progressIntervalRef.current) {
      clearInterval(progressIntervalRef.current);
      progressIntervalRef.current = null;
    }
    setActiveDataSourceId(null);
    setIngestionProgress(null);
  };

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
    setIngestionProgress(null);

    try {
      // Start the ingestion - this returns quickly with data_source_id
      const result = await api.ingestGitRepository({
        workspace_id: parseInt(workspaceId),
        name: gitForm.name,
        repo_url: gitForm.repo_url,
        branch: gitForm.branch,
        username: gitForm.username || undefined,
        token: gitForm.token || undefined,
        language_filter: gitForm.language_filter,
        max_depth: gitForm.max_depth ? parseInt(gitForm.max_depth.toString()) : undefined
      });

      if (result.data_source_id) {
        // Start polling for progress
        startProgressPolling(result.data_source_id);
        
        // Poll until completion
        const checkCompletion = setInterval(async () => {
          try {
            const progress = await api.getIngestionProgress(result.data_source_id);
            
            if (!progress.in_progress || progress.status === 'completed' || progress.status === 'failed') {
              clearInterval(checkCompletion);
              stopProgressPolling();
              setLoading(false);
              
              if (progress.status === 'completed') {
                setSuccess('Successfully ingested repository');
                setGitForm({ name: '', repo_url: '', branch: 'main', username: '', token: '', language_filter: 'all', max_depth: '' });
                loadWorkspaceData();
              } else if (progress.status === 'failed') {
                setError('Ingestion failed. Check server logs for details.');
              }
            }
          } catch (err) {
            console.error('Error checking completion:', err);
          }
        }, 2000);
      } else if (!result.success) {
        setError(result.error || 'Failed to start Git repository ingestion');
        setLoading(false);
      }
    } catch (err) {
      setError('Failed to ingest Git repository');
      console.error('Git ingestion error:', err);
      stopProgressPolling();
      setLoading(false);
    }
  };

  const handleConfluenceSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!workspaceId) return;

    setLoading(true);
    setError('');
    setSuccess('');
    setIngestionProgress(null);

    try {
      // Parse page_ids if provided
      const pageIds = confluenceForm.page_ids
        ? confluenceForm.page_ids.split(',').map(id => id.trim()).filter(id => id)
        : undefined;

      const result = await api.ingestConfluenceSpace({
        workspace_id: parseInt(workspaceId),
        name: confluenceForm.name,
        space_key: confluenceForm.space_key,
        base_url: confluenceForm.base_url || undefined,
        username: confluenceForm.username || undefined,
        api_token: confluenceForm.api_token || undefined,
        page_ids: pageIds,
        max_depth: confluenceForm.max_depth ? parseInt(confluenceForm.max_depth.toString()) : undefined,
        include_children: confluenceForm.include_children
      });

      if (result.success) {
        setSuccess(`Successfully ingested ${result.documents_count} documents from Confluence space`);
        setConfluenceForm({ name: '', space_key: '', base_url: '', username: '', api_token: '', page_ids: '', max_depth: '', include_children: true });
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

  const handleJiraSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!workspaceId) return;

    setLoading(true);
    setError('');
    setSuccess('');
    setIngestionProgress(null);

    try {
      // Parse specific_tickets if provided
      const specificTickets = jiraForm.specific_tickets
        ? jiraForm.specific_tickets.split(',').map(t => t.trim()).filter(t => t)
        : undefined;

      const result = await api.ingestJiraProject({
        workspace_id: parseInt(workspaceId),
        name: jiraForm.name,
        project_key: jiraForm.project_key,
        base_url: jiraForm.base_url || undefined,
        username: jiraForm.username || undefined,
        api_token: jiraForm.api_token || undefined,
        issue_types: jiraForm.issue_types.length > 0 ? jiraForm.issue_types : undefined,
        specific_tickets: specificTickets,
        max_results: jiraForm.max_results ? parseInt(jiraForm.max_results.toString()) : undefined
      });

      if (result.data_source_id) {
        // Start polling for progress
        startProgressPolling(result.data_source_id);
        
        // Poll until completion
        const checkCompletion = setInterval(async () => {
          try {
            const progress = await api.getIngestionProgress(result.data_source_id);
            
            if (!progress.in_progress || progress.status === 'completed' || progress.status === 'failed') {
              clearInterval(checkCompletion);
              stopProgressPolling();
              setLoading(false);
              
              if (progress.status === 'completed') {
                setSuccess('Successfully ingested JIRA issues');
                setJiraForm({ name: '', project_key: '', base_url: '', username: '', api_token: '', issue_types: [], specific_tickets: '', max_results: '' });
                loadWorkspaceData();
              } else if (progress.status === 'failed') {
                setError('JIRA ingestion failed. Check server logs for details.');
              }
            }
          } catch (err) {
            console.error('Error checking completion:', err);
          }
        }, 2000);
      } else if (!result.success) {
        setError(result.error || 'Failed to start JIRA ingestion');
        setLoading(false);
      }
    } catch (err) {
      setError('Failed to ingest JIRA project');
      console.error('JIRA ingestion error:', err);
      stopProgressPolling();
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
    if (!workspaceId || (codeForm.files.length === 0 && !codeForm.directoryPath)) return;

    setLoading(true);
    setError('');
    setSuccess('');
    setCodeStats(null);

    try {
      let result;
      
      if (codeForm.directoryPath) {
        // Use directory ingestion
        result = await api.ingestCodeDirectory(
          parseInt(workspaceId),
          codeForm.name || 'Code Directory',
          codeForm.directoryPath,
          codeForm.maxDepth ? parseInt(codeForm.maxDepth.toString()) : undefined,
          codeForm.includeHeaders
        );
      } else {
        // Use file upload ingestion
        result = await api.ingestCodeFiles(
          parseInt(workspaceId),
          codeForm.name || 'Code Files',
          codeForm.files
        );
      }

      if (result.success) {
        setCodeStats(result.stats);
        setSuccess(`Successfully processed ${result.stats.files_processed} files: ${result.stats.functions_extracted} functions, ${result.stats.classes_extracted} classes, ${result.stats.structs_extracted} structs`);
        setCodeForm({ name: '', files: [], directoryPath: '', maxDepth: '', includeHeaders: true });
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
                onClick={() => setActiveTab('jira')}
                className={`py-2 px-1 border-b-2 font-medium text-sm ${
                  activeTab === 'jira'
                    ? 'border-primary-500 text-primary-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                }`}
              >
                <Ticket className="h-4 w-4 inline mr-2" />
                JIRA
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

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
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
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Max Depth (optional)
                    </label>
                    <input
                      type="number"
                      min="1"
                      value={gitForm.max_depth}
                      onChange={(e) => setGitForm({ ...gitForm, max_depth: e.target.value })}
                      className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-primary-500 focus:border-primary-500"
                      placeholder="Unlimited"
                    />
                    <p className="text-xs text-gray-500 mt-1">Limit directory depth to scan</p>
                  </div>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Language Filter
                  </label>
                  <select
                    value={gitForm.language_filter}
                    onChange={(e) => setGitForm({ ...gitForm, language_filter: e.target.value })}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-primary-500 focus:border-primary-500"
                  >
                    {LANGUAGE_OPTIONS.map((opt) => (
                      <option key={opt.value} value={opt.value}>
                        {opt.label} - {opt.description}
                      </option>
                    ))}
                  </select>
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

                {/* Progress Bar */}
                {loading && (
                  <div className="bg-blue-50 rounded-lg p-4 border border-blue-200">
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-sm font-medium text-blue-800">
                        {ingestionProgress?.stage || 'Starting...'}
                      </span>
                      <div className="flex items-center gap-3">
                        <span className="text-sm text-blue-600">
                          Stage {ingestionProgress?.stage_num || 1}/{ingestionProgress?.total_stages || 4}
                        </span>
                        <button
                          type="button"
                          onClick={handleCancelIngestion}
                          className="flex items-center gap-1 px-2 py-1 text-xs font-medium text-red-600 hover:text-red-700 hover:bg-red-100 rounded transition-colors"
                          title="Cancel ingestion"
                        >
                          <X className="h-3 w-3" />
                          Cancel
                        </button>
                      </div>
                    </div>
                    
                    {/* Stage Progress Bar */}
                    <div className="w-full bg-blue-200 rounded-full h-2 mb-2">
                      <div
                        className="bg-blue-600 h-2 rounded-full transition-all duration-300"
                        style={{ 
                          width: `${((ingestionProgress?.stage_num || 1) / (ingestionProgress?.total_stages || 4)) * 100}%` 
                        }}
                      />
                    </div>
                    
                    {/* Item Progress (if available) */}
                    {ingestionProgress && ingestionProgress.total > 0 && (
                      <div className="mt-3">
                        <div className="flex items-center justify-between mb-1">
                          <span className="text-xs text-blue-700">
                            {ingestionProgress.message}
                          </span>
                          <span className="text-xs text-blue-600">
                            {ingestionProgress.current}/{ingestionProgress.total}
                          </span>
                        </div>
                        <div className="w-full bg-blue-100 rounded-full h-1.5">
                          <div
                            className="bg-blue-500 h-1.5 rounded-full transition-all duration-300"
                            style={{ width: `${ingestionProgress.percent}%` }}
                          />
                        </div>
                      </div>
                    )}
                    
                    {/* Stage Indicators */}
                    <div className="flex justify-between mt-4 text-xs">
                      <div className={`flex flex-col items-center ${(ingestionProgress?.stage_num || 0) >= 1 ? 'text-blue-600' : 'text-gray-400'}`}>
                        <div className={`w-6 h-6 rounded-full flex items-center justify-center mb-1 ${(ingestionProgress?.stage_num || 0) >= 1 ? 'bg-blue-600 text-white' : 'bg-gray-200'}`}>
                          {(ingestionProgress?.stage_num || 0) > 1 ? <CheckCircle className="w-4 h-4" /> : '1'}
                        </div>
                        <span>Clone</span>
                      </div>
                      <div className={`flex flex-col items-center ${(ingestionProgress?.stage_num || 0) >= 2 ? 'text-blue-600' : 'text-gray-400'}`}>
                        <div className={`w-6 h-6 rounded-full flex items-center justify-center mb-1 ${(ingestionProgress?.stage_num || 0) >= 2 ? 'bg-blue-600 text-white' : 'bg-gray-200'}`}>
                          {(ingestionProgress?.stage_num || 0) > 2 ? <CheckCircle className="w-4 h-4" /> : '2'}
                        </div>
                        <span>Process</span>
                      </div>
                      <div className={`flex flex-col items-center ${(ingestionProgress?.stage_num || 0) >= 3 ? 'text-blue-600' : 'text-gray-400'}`}>
                        <div className={`w-6 h-6 rounded-full flex items-center justify-center mb-1 ${(ingestionProgress?.stage_num || 0) >= 3 ? 'bg-blue-600 text-white' : 'bg-gray-200'}`}>
                          {(ingestionProgress?.stage_num || 0) > 3 ? <CheckCircle className="w-4 h-4" /> : '3'}
                        </div>
                        <span>Embed</span>
                      </div>
                      <div className={`flex flex-col items-center ${(ingestionProgress?.stage_num || 0) >= 4 ? 'text-blue-600' : 'text-gray-400'}`}>
                        <div className={`w-6 h-6 rounded-full flex items-center justify-center mb-1 ${(ingestionProgress?.stage_num || 0) >= 4 ? 'bg-blue-600 text-white' : 'bg-gray-200'}`}>
                          {(ingestionProgress?.stage_num || 0) >= 4 ? <CheckCircle className="w-4 h-4" /> : '4'}
                        </div>
                        <span>Done</span>
                      </div>
                    </div>
                  </div>
                )}

                <div className="flex gap-2">
                  <button
                    type="submit"
                    disabled={loading}
                    className="flex-1 flex items-center justify-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-primary-600 hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500 disabled:opacity-50"
                  >
                    {loading ? (
                      <Loader2 className="h-4 w-4 animate-spin mr-2" />
                    ) : (
                      <GitBranch className="h-4 w-4 mr-2" />
                    )}
                    {loading ? 'Ingesting...' : 'Ingest Repository'}
                  </button>
                  <button
                    type="button"
                    onClick={() => {
                      clearGitCache();
                      setGitForm({ name: '', repo_url: '', branch: 'main', username: '', token: '', language_filter: 'all', max_depth: '' });
                    }}
                    className="px-3 py-2 border border-gray-300 text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500"
                    title="Clear cached form data"
                  >
                    <RotateCcw className="h-4 w-4" />
                  </button>
                </div>
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
                      Token / Password
                    </label>
                    <input
                      type="password"
                      value={confluenceForm.api_token}
                      onChange={(e) => setConfluenceForm({ ...confluenceForm, api_token: e.target.value })}
                      className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-primary-500 focus:border-primary-500"
                      placeholder="PAT, API token, or password"
                    />
                    <p className="text-xs text-gray-500 mt-1">For PAT: leave username empty. For basic auth: enter username + password</p>
                  </div>
                </div>

                {/* Page Selection Options */}
                <div className="p-4 bg-gray-50 rounded-md">
                  <h4 className="text-sm font-medium text-gray-700 mb-3">Page Selection (Optional)</h4>
                  <div className="space-y-3">
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">
                        Specific Page IDs
                      </label>
                      <input
                        type="text"
                        value={confluenceForm.page_ids}
                        onChange={(e) => setConfluenceForm({ ...confluenceForm, page_ids: e.target.value })}
                        className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-primary-500 focus:border-primary-500"
                        placeholder="123456, 789012 (comma-separated)"
                      />
                      <p className="text-xs text-gray-500 mt-1">Leave empty to fetch all pages from the space</p>
                    </div>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">
                          Max Depth
                        </label>
                        <input
                          type="number"
                          min="0"
                          value={confluenceForm.max_depth}
                          onChange={(e) => setConfluenceForm({ ...confluenceForm, max_depth: e.target.value })}
                          className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-primary-500 focus:border-primary-500"
                          placeholder="Unlimited"
                        />
                        <p className="text-xs text-gray-500 mt-1">0 = root pages only</p>
                      </div>
                      <div className="flex items-center pt-6">
                        <input
                          type="checkbox"
                          id="includeChildren"
                          checked={confluenceForm.include_children}
                          onChange={(e) => setConfluenceForm({ ...confluenceForm, include_children: e.target.checked })}
                          className="h-4 w-4 text-primary-600 focus:ring-primary-500 border-gray-300 rounded"
                        />
                        <label htmlFor="includeChildren" className="ml-2 text-sm text-gray-700">
                          Include child pages
                        </label>
                      </div>
                    </div>
                  </div>
                </div>

                <div className="flex gap-2">
                  <button
                    type="submit"
                    disabled={loading}
                    className="flex-1 flex items-center justify-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-primary-600 hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500 disabled:opacity-50"
                  >
                    {loading ? (
                      <Loader2 className="h-4 w-4 animate-spin mr-2" />
                    ) : (
                      <Globe className="h-4 w-4 mr-2" />
                    )}
                    Ingest Space
                  </button>
                  <button
                    type="button"
                    onClick={() => {
                      clearConfluenceCache();
                      setConfluenceForm({ name: '', space_key: '', base_url: '', username: '', api_token: '', page_ids: '', max_depth: '', include_children: true });
                    }}
                    className="px-3 py-2 border border-gray-300 text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500"
                    title="Clear cached form data"
                  >
                    <RotateCcw className="h-4 w-4" />
                  </button>
                </div>
              </form>
            </div>
          )}

          {/* JIRA Form */}
          {activeTab === 'jira' && (
            <div className="bg-white rounded-lg shadow p-6">
              <h3 className="text-lg font-medium text-gray-900 mb-4">Ingest JIRA Project</h3>
              <form onSubmit={handleJiraSubmit} className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Name
                  </label>
                  <input
                    type="text"
                    required
                    value={jiraForm.name}
                    onChange={(e) => setJiraForm({ ...jiraForm, name: e.target.value })}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-primary-500 focus:border-primary-500"
                    placeholder="Project Issues"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Project Key
                  </label>
                  <input
                    type="text"
                    required
                    value={jiraForm.project_key}
                    onChange={(e) => setJiraForm({ ...jiraForm, project_key: e.target.value.toUpperCase() })}
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
                    value={jiraForm.base_url}
                    onChange={(e) => setJiraForm({ ...jiraForm, base_url: e.target.value })}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-primary-500 focus:border-primary-500"
                    placeholder="https://company.atlassian.net"
                  />
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Username / Email
                    </label>
                    <input
                      type="text"
                      value={jiraForm.username}
                      onChange={(e) => setJiraForm({ ...jiraForm, username: e.target.value })}
                      className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-primary-500 focus:border-primary-500"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Token / Password
                    </label>
                    <input
                      type="password"
                      value={jiraForm.api_token}
                      onChange={(e) => setJiraForm({ ...jiraForm, api_token: e.target.value })}
                      className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-primary-500 focus:border-primary-500"
                      placeholder="PAT, API token, or password"
                    />
                    <p className="text-xs text-gray-500 mt-1">For PAT: leave username empty. For basic auth: enter username + password</p>
                  </div>
                </div>

                {/* Issue Type Selection */}
                <div className="p-4 bg-gray-50 rounded-md">
                  <h4 className="text-sm font-medium text-gray-700 mb-3">Issue Type Filter (Optional)</h4>
                  <div className="flex flex-wrap gap-2">
                    {JIRA_ISSUE_TYPES.map((type) => (
                      <label key={type.value} className="inline-flex items-center">
                        <input
                          type="checkbox"
                          checked={jiraForm.issue_types.includes(type.value)}
                          onChange={(e) => {
                            if (e.target.checked) {
                              setJiraForm({ ...jiraForm, issue_types: [...jiraForm.issue_types, type.value] });
                            } else {
                              setJiraForm({ ...jiraForm, issue_types: jiraForm.issue_types.filter(t => t !== type.value) });
                            }
                          }}
                          className="h-4 w-4 text-primary-600 focus:ring-primary-500 border-gray-300 rounded"
                        />
                        <span className="ml-2 text-sm text-gray-700">{type.label}</span>
                      </label>
                    ))}
                  </div>
                  <p className="text-xs text-gray-500 mt-2">Leave all unchecked to fetch all issue types</p>
                </div>

                {/* Specific Tickets */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Specific Tickets (Optional)
                  </label>
                  <input
                    type="text"
                    value={jiraForm.specific_tickets}
                    onChange={(e) => setJiraForm({ ...jiraForm, specific_tickets: e.target.value.toUpperCase() })}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-primary-500 focus:border-primary-500"
                    placeholder="PROJ-123, PROJ-456 (comma-separated)"
                  />
                  <p className="text-xs text-gray-500 mt-1">Overrides project-wide fetch if specified</p>
                </div>

                {/* Max Results */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Max Results (Optional)
                  </label>
                  <input
                    type="number"
                    min="1"
                    value={jiraForm.max_results}
                    onChange={(e) => setJiraForm({ ...jiraForm, max_results: e.target.value })}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-primary-500 focus:border-primary-500"
                    placeholder="Unlimited"
                  />
                  <p className="text-xs text-gray-500 mt-1">Limit the number of issues to fetch</p>
                </div>

                {/* Progress Bar */}
                {loading && ingestionProgress && (
                  <div className="bg-blue-50 rounded-lg p-4 border border-blue-200">
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-sm font-medium text-blue-800">
                        {ingestionProgress.stage || 'Starting...'}
                      </span>
                      <div className="flex items-center gap-3">
                        <span className="text-sm text-blue-600">
                          Stage {ingestionProgress.stage_num || 1}/{ingestionProgress.total_stages || 4}
                        </span>
                        <button
                          type="button"
                          onClick={handleCancelIngestion}
                          className="flex items-center gap-1 px-2 py-1 text-xs font-medium text-red-600 hover:text-red-700 hover:bg-red-100 rounded transition-colors"
                          title="Cancel ingestion"
                        >
                          <X className="h-3 w-3" />
                          Cancel
                        </button>
                      </div>
                    </div>
                    <div className="w-full bg-blue-200 rounded-full h-2">
                      <div
                        className="bg-blue-600 h-2 rounded-full transition-all duration-300"
                        style={{ 
                          width: `${((ingestionProgress.stage_num || 1) / (ingestionProgress.total_stages || 4)) * 100}%` 
                        }}
                      />
                    </div>
                    {ingestionProgress.message && (
                      <p className="text-xs text-blue-700 mt-2">{ingestionProgress.message}</p>
                    )}
                  </div>
                )}

                <div className="flex gap-2">
                  <button
                    type="submit"
                    disabled={loading}
                    className="flex-1 flex items-center justify-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-primary-600 hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500 disabled:opacity-50"
                  >
                    {loading ? (
                      <Loader2 className="h-4 w-4 animate-spin mr-2" />
                    ) : (
                      <Ticket className="h-4 w-4 mr-2" />
                    )}
                    {loading ? 'Ingesting...' : 'Ingest JIRA Issues'}
                  </button>
                  <button
                    type="button"
                    onClick={() => {
                      clearJiraCache();
                      setJiraForm({ name: '', project_key: '', base_url: '', username: '', api_token: '', issue_types: [], specific_tickets: '', max_results: '' });
                    }}
                    className="px-3 py-2 border border-gray-300 text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500"
                    title="Clear cached form data"
                  >
                    <RotateCcw className="h-4 w-4" />
                  </button>
                </div>
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
                Upload C/C++ source files or specify a local directory for AST-based parsing. Functions, classes, and structs will be 
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

                {/* Directory Path Option */}
                <div className="p-4 bg-gray-50 rounded-md">
                  <h4 className="text-sm font-medium text-gray-700 mb-3">Option 1: Local Directory</h4>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Directory Path
                    </label>
                    <input
                      type="text"
                      value={codeForm.directoryPath}
                      onChange={(e) => setCodeForm({ ...codeForm, directoryPath: e.target.value })}
                      className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-primary-500 focus:border-primary-500"
                      placeholder="/path/to/your/code/directory"
                    />
                    <p className="text-xs text-gray-500 mt-1">
                      Full path to a local directory containing C/C++ source files
                    </p>
                  </div>
                  
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mt-3">
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">
                        Max Depth (optional)
                      </label>
                      <input
                        type="number"
                        min="1"
                        value={codeForm.maxDepth}
                        onChange={(e) => setCodeForm({ ...codeForm, maxDepth: e.target.value })}
                        className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-primary-500 focus:border-primary-500"
                        placeholder="Unlimited"
                      />
                      <p className="text-xs text-gray-500 mt-1">Limit subdirectory depth</p>
                    </div>
                    <div className="flex items-center pt-6">
                      <input
                        type="checkbox"
                        id="includeHeaders"
                        checked={codeForm.includeHeaders}
                        onChange={(e) => setCodeForm({ ...codeForm, includeHeaders: e.target.checked })}
                        className="h-4 w-4 text-primary-600 focus:ring-primary-500 border-gray-300 rounded"
                      />
                      <label htmlFor="includeHeaders" className="ml-2 text-sm text-gray-700">
                        Include header files (.h, .hpp)
                      </label>
                    </div>
                  </div>
                </div>

                {/* File Upload Option */}
                <div className="p-4 bg-gray-50 rounded-md">
                  <h4 className="text-sm font-medium text-gray-700 mb-3">Option 2: Upload Files</h4>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Source Files
                    </label>
                    <input
                      type="file"
                      multiple
                      accept=".c,.h,.cpp,.cc,.cxx,.hpp,.hxx,.hh"
                      onChange={(e) => setCodeForm({ ...codeForm, files: Array.from(e.target.files || []) })}
                      className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-primary-500 focus:border-primary-500"
                    />
                    <p className="text-xs text-gray-500 mt-1">
                      Supported: .c, .h, .cpp, .cc, .cxx, .hpp, .hxx, .hh
                    </p>
                  </div>
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

                <div className="flex gap-2">
                  <button
                    type="submit"
                    disabled={loading || (codeForm.files.length === 0 && !codeForm.directoryPath)}
                    className="flex-1 flex items-center justify-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-primary-600 hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500 disabled:opacity-50"
                  >
                    {loading ? (
                      <>
                        <Loader2 className="h-4 w-4 animate-spin mr-2" />
                        Processing (this may take a while)...
                      </>
                    ) : (
                      <>
                        <Code className="h-4 w-4 mr-2" />
                        {codeForm.directoryPath ? 'Ingest Directory' : `Ingest ${codeForm.files.length} Code File${codeForm.files.length !== 1 ? 's' : ''}`}
                      </>
                    )}
                  </button>
                  <button
                    type="button"
                    onClick={() => {
                      clearCodeCache();
                      setCodeForm({ name: '', files: [], directoryPath: '', maxDepth: '', includeHeaders: true });
                    }}
                    className="px-3 py-2 border border-gray-300 text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500"
                    title="Clear cached form data"
                  >
                    <RotateCcw className="h-4 w-4" />
                  </button>
                </div>
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

import React, { useState, useEffect } from 'react';
import { useParams } from 'react-router-dom';
import { 
  Search, 
  FileCode, 
  ChevronRight, 
  ChevronDown, 
  Loader2, 
  Eye,
  Hash,
  Layers,
  FileText,
  Code,
  Filter
} from 'lucide-react';
import { api } from '../services/api';

interface EmbeddingDocument {
  id: number;
  title: string;
  file_path: string;
  file_type: string;
  chunk_count: number;
  data_source_id: number;
  data_source_name: string;
  created_at: string;
}

interface EmbeddingChunk {
  id: number;
  chunk_index: number;
  content: string;
  start_line?: number;
  end_line?: number;
  metadata: Record<string, any>;
}

interface GroupedDocuments {
  [dataSourceName: string]: EmbeddingDocument[];
}

export function EmbeddingsViewer() {
  const { workspaceId } = useParams<{ workspaceId: string }>();
  const [documents, setDocuments] = useState<EmbeddingDocument[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedDocument, setSelectedDocument] = useState<EmbeddingDocument | null>(null);
  const [chunks, setChunks] = useState<EmbeddingChunk[]>([]);
  const [loadingChunks, setLoadingChunks] = useState(false);
  const [expandedSources, setExpandedSources] = useState<Set<string>>(new Set());
  const [fileTypeFilter, setFileTypeFilter] = useState<string>('all');

  useEffect(() => {
    if (workspaceId) {
      loadDocuments();
    }
  }, [workspaceId]);

  const loadDocuments = async () => {
    try {
      setLoading(true);
      setError('');
      const data = await api.getWorkspaceEmbeddings(parseInt(workspaceId!));
      setDocuments(data);
      // Auto-expand all sources
      const sources = new Set<string>(data.map((d: EmbeddingDocument) => d.data_source_name));
      setExpandedSources(sources);
    } catch (err) {
      setError('Failed to load embeddings');
      console.error('Error loading embeddings:', err);
    } finally {
      setLoading(false);
    }
  };

  const loadChunks = async (document: EmbeddingDocument) => {
    try {
      setLoadingChunks(true);
      setSelectedDocument(document);
      const data = await api.getDocumentChunks(document.id);
      setChunks(data);
    } catch (err) {
      console.error('Error loading chunks:', err);
    } finally {
      setLoadingChunks(false);
    }
  };

  const toggleSource = (sourceName: string) => {
    setExpandedSources(prev => {
      const next = new Set(prev);
      if (next.has(sourceName)) {
        next.delete(sourceName);
      } else {
        next.add(sourceName);
      }
      return next;
    });
  };

  const getFileIcon = (fileType: string) => {
    if (fileType === 'code' || ['py', 'js', 'ts', 'tsx', 'c', 'cpp', 'h', 'hpp', 'java', 'go', 'rs'].includes(fileType)) {
      return <Code className="h-4 w-4 text-green-500" />;
    }
    if (fileType === 'jira') {
      return <FileText className="h-4 w-4 text-blue-500" />;
    }
    if (fileType === 'confluence') {
      return <FileText className="h-4 w-4 text-blue-600" />;
    }
    return <FileCode className="h-4 w-4 text-gray-500" />;
  };

  // Filter and group documents
  const filteredDocuments = documents.filter(doc => {
    const matchesSearch = searchQuery === '' || 
      doc.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
      doc.file_path.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesType = fileTypeFilter === 'all' || doc.file_type === fileTypeFilter;
    return matchesSearch && matchesType;
  });

  const groupedDocuments: GroupedDocuments = filteredDocuments.reduce((acc, doc) => {
    const source = doc.data_source_name || 'Unknown Source';
    if (!acc[source]) {
      acc[source] = [];
    }
    acc[source].push(doc);
    return acc;
  }, {} as GroupedDocuments);

  // Get unique file types for filter
  const fileTypes = Array.from(new Set(documents.map(d => d.file_type))).filter(Boolean);

  // Stats
  const totalDocuments = documents.length;
  const totalChunks = documents.reduce((sum, d) => sum + d.chunk_count, 0);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="h-8 w-8 animate-spin text-primary-600" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-6">
        <div className="bg-red-50 text-red-700 p-4 rounded-lg">{error}</div>
      </div>
    );
  }

  return (
    <div className="flex h-full">
      {/* Left Panel - Document Tree */}
      <div className="w-1/3 border-r border-gray-200 flex flex-col">
        {/* Header */}
        <div className="p-4 border-b border-gray-200">
          <h2 className="text-lg font-semibold text-gray-900 flex items-center gap-2">
            <Layers className="h-5 w-5" />
            Embeddings Explorer
          </h2>
          <p className="text-sm text-gray-600 mt-1">
            {totalDocuments} documents, {totalChunks} chunks
          </p>
        </div>

        {/* Search and Filter */}
        <div className="p-4 space-y-3 border-b border-gray-200">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search documents..."
              className="w-full pl-10 pr-4 py-2 text-sm border border-gray-300 rounded-md focus:ring-primary-500 focus:border-primary-500"
            />
          </div>
          <div className="flex items-center gap-2">
            <Filter className="h-4 w-4 text-gray-400" />
            <select
              value={fileTypeFilter}
              onChange={(e) => setFileTypeFilter(e.target.value)}
              className="flex-1 text-sm border border-gray-300 rounded-md px-2 py-1 focus:ring-primary-500 focus:border-primary-500"
            >
              <option value="all">All Types</option>
              {fileTypes.map(type => (
                <option key={type} value={type}>{type}</option>
              ))}
            </select>
          </div>
        </div>

        {/* Document Tree */}
        <div className="flex-1 overflow-y-auto p-2">
          {Object.keys(groupedDocuments).length === 0 ? (
            <div className="text-center text-gray-500 py-8">
              No documents found
            </div>
          ) : (
            Object.entries(groupedDocuments).map(([sourceName, docs]) => (
              <div key={sourceName} className="mb-2">
                {/* Source Header */}
                <button
                  onClick={() => toggleSource(sourceName)}
                  className="w-full flex items-center gap-2 px-2 py-1.5 text-sm font-medium text-gray-700 hover:bg-gray-100 rounded"
                >
                  {expandedSources.has(sourceName) ? (
                    <ChevronDown className="h-4 w-4" />
                  ) : (
                    <ChevronRight className="h-4 w-4" />
                  )}
                  <span className="truncate">{sourceName}</span>
                  <span className="ml-auto text-xs text-gray-500 bg-gray-100 px-1.5 py-0.5 rounded">
                    {docs.length}
                  </span>
                </button>

                {/* Documents */}
                {expandedSources.has(sourceName) && (
                  <div className="ml-4 space-y-0.5">
                    {docs.map(doc => (
                      <button
                        key={doc.id}
                        onClick={() => loadChunks(doc)}
                        className={`w-full flex items-center gap-2 px-2 py-1.5 text-sm rounded transition-colors ${
                          selectedDocument?.id === doc.id
                            ? 'bg-primary-100 text-primary-700'
                            : 'text-gray-600 hover:bg-gray-50'
                        }`}
                      >
                        {getFileIcon(doc.file_type)}
                        <span className="truncate flex-1 text-left">{doc.title || doc.file_path}</span>
                        <span className="text-xs text-gray-400 flex items-center gap-1">
                          <Hash className="h-3 w-3" />
                          {doc.chunk_count}
                        </span>
                      </button>
                    ))}
                  </div>
                )}
              </div>
            ))
          )}
        </div>
      </div>

      {/* Right Panel - Chunk Details */}
      <div className="flex-1 flex flex-col">
        {selectedDocument ? (
          <>
            {/* Document Header */}
            <div className="p-4 border-b border-gray-200 bg-gray-50">
              <div className="flex items-center gap-2">
                {getFileIcon(selectedDocument.file_type)}
                <h3 className="font-medium text-gray-900 truncate">
                  {selectedDocument.title || selectedDocument.file_path}
                </h3>
              </div>
              <p className="text-sm text-gray-600 mt-1">
                {selectedDocument.file_path}
              </p>
              <div className="flex items-center gap-4 mt-2 text-xs text-gray-500">
                <span>Type: {selectedDocument.file_type}</span>
                <span>Chunks: {selectedDocument.chunk_count}</span>
              </div>
            </div>

            {/* Chunks List */}
            <div className="flex-1 overflow-y-auto p-4">
              {loadingChunks ? (
                <div className="flex items-center justify-center h-32">
                  <Loader2 className="h-6 w-6 animate-spin text-primary-600" />
                </div>
              ) : chunks.length === 0 ? (
                <div className="text-center text-gray-500 py-8">
                  No chunks found
                </div>
              ) : (
                <div className="space-y-4">
                  {chunks.map((chunk, index) => (
                    <div
                      key={chunk.id}
                      className="border border-gray-200 rounded-lg overflow-hidden"
                    >
                      {/* Chunk Header */}
                      <div className="bg-gray-50 px-4 py-2 flex items-center justify-between border-b border-gray-200">
                        <div className="flex items-center gap-3">
                          <span className="text-sm font-medium text-gray-700">
                            Chunk {chunk.chunk_index + 1}
                          </span>
                          {chunk.start_line && chunk.end_line && (
                            <span className="text-xs text-gray-500 bg-gray-100 px-2 py-0.5 rounded">
                              Lines {chunk.start_line}-{chunk.end_line}
                            </span>
                          )}
                        </div>
                        <span className="text-xs text-gray-500">
                          {chunk.content.length} chars
                        </span>
                      </div>

                      {/* Chunk Content */}
                      <div className="p-4">
                        <pre className="text-sm text-gray-700 whitespace-pre-wrap font-mono bg-gray-50 p-3 rounded overflow-x-auto max-h-64">
                          {chunk.content}
                        </pre>
                      </div>

                      {/* Chunk Metadata */}
                      {Object.keys(chunk.metadata || {}).length > 0 && (
                        <div className="bg-gray-50 px-4 py-2 border-t border-gray-200">
                          <details className="text-xs">
                            <summary className="cursor-pointer text-gray-600 hover:text-gray-800">
                              Metadata
                            </summary>
                            <pre className="mt-2 text-gray-600 overflow-x-auto">
                              {JSON.stringify(chunk.metadata, null, 2)}
                            </pre>
                          </details>
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>
          </>
        ) : (
          <div className="flex-1 flex items-center justify-center text-gray-500">
            <div className="text-center">
              <Eye className="h-12 w-12 mx-auto mb-4 text-gray-300" />
              <p>Select a document to view its embeddings</p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

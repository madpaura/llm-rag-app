import React, { useState, useEffect, useRef } from 'react';
import { X, FileText, ChevronUp, ChevronDown, Copy, Check } from 'lucide-react';
import { api, DocumentContent } from '../services/api';

interface DocumentViewerProps {
  documentId: number;
  chunkId?: number;
  startLine?: number;
  endLine?: number;
  onClose: () => void;
}

export function DocumentViewer({ 
  documentId, 
  chunkId, 
  startLine, 
  endLine, 
  onClose 
}: DocumentViewerProps) {
  const [document, setDocument] = useState<DocumentContent | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [copied, setCopied] = useState(false);
  const highlightRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    loadDocument();
  }, [documentId]);

  useEffect(() => {
    // Scroll to highlighted section after document loads
    if (document && highlightRef.current) {
      setTimeout(() => {
        highlightRef.current?.scrollIntoView({ behavior: 'smooth', block: 'center' });
      }, 100);
    }
  }, [document, startLine]);

  const loadDocument = async () => {
    try {
      setLoading(true);
      const doc = await api.getDocument(documentId);
      setDocument(doc);
    } catch (err) {
      console.error('Error loading document:', err);
      setError('Failed to load document');
    } finally {
      setLoading(false);
    }
  };

  const copyToClipboard = async () => {
    if (!document) return;
    
    const textToCopy = startLine && endLine 
      ? document.lines.slice(startLine - 1, endLine).join('\n')
      : document.content;
    
    await navigator.clipboard.writeText(textToCopy);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const isLineHighlighted = (lineNum: number) => {
    if (!startLine || !endLine) return false;
    return lineNum >= startLine && lineNum <= endLine;
  };

  if (loading) {
    return (
      <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
        <div className="bg-white rounded-lg p-8">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600 mx-auto"></div>
          <p className="mt-4 text-gray-600">Loading document...</p>
        </div>
      </div>
    );
  }

  if (error || !document) {
    return (
      <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
        <div className="bg-white rounded-lg p-8 max-w-md">
          <p className="text-red-600">{error || 'Document not found'}</p>
          <button
            onClick={onClose}
            className="mt-4 px-4 py-2 bg-gray-200 rounded hover:bg-gray-300"
          >
            Close
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-lg shadow-xl w-full max-w-4xl max-h-[90vh] flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-gray-200">
          <div className="flex items-center space-x-3">
            <FileText className="h-5 w-5 text-primary-600" />
            <div>
              <h2 className="font-semibold text-gray-900">{document.title}</h2>
              {document.file_path && (
                <p className="text-sm text-gray-500">{document.file_path}</p>
              )}
            </div>
          </div>
          <div className="flex items-center space-x-2">
            {startLine && endLine && (
              <span className="text-sm text-primary-600 bg-primary-50 px-2 py-1 rounded">
                Lines {startLine}-{endLine}
              </span>
            )}
            <button
              onClick={copyToClipboard}
              className="p-2 text-gray-500 hover:text-gray-700 hover:bg-gray-100 rounded"
              title="Copy content"
            >
              {copied ? <Check className="h-4 w-4 text-green-500" /> : <Copy className="h-4 w-4" />}
            </button>
            <button
              onClick={onClose}
              className="p-2 text-gray-500 hover:text-gray-700 hover:bg-gray-100 rounded"
            >
              <X className="h-5 w-5" />
            </button>
          </div>
        </div>

        {/* Navigation */}
        {startLine && (
          <div className="flex items-center justify-between px-4 py-2 bg-gray-50 border-b text-sm">
            <span className="text-gray-600">
              Showing highlighted section (lines {startLine}-{endLine})
            </span>
            <div className="flex items-center space-x-2">
              <button
                onClick={() => highlightRef.current?.scrollIntoView({ behavior: 'smooth', block: 'center' })}
                className="flex items-center space-x-1 text-primary-600 hover:text-primary-700"
              >
                <ChevronDown className="h-4 w-4" />
                <span>Go to highlight</span>
              </button>
            </div>
          </div>
        )}

        {/* Content */}
        <div className="flex-1 overflow-auto">
          <div className="font-mono text-sm">
            {document.lines.map((line, index) => {
              const lineNum = index + 1;
              const isHighlighted = isLineHighlighted(lineNum);
              const isFirstHighlighted = lineNum === startLine;
              
              return (
                <div
                  key={index}
                  ref={isFirstHighlighted ? highlightRef : undefined}
                  className={`flex ${
                    isHighlighted 
                      ? 'bg-yellow-100 border-l-4 border-yellow-400' 
                      : 'hover:bg-gray-50'
                  }`}
                >
                  <div className={`w-12 flex-shrink-0 text-right pr-3 py-0.5 select-none ${
                    isHighlighted ? 'text-yellow-700 bg-yellow-200' : 'text-gray-400 bg-gray-50'
                  }`}>
                    {lineNum}
                  </div>
                  <pre className="flex-1 py-0.5 px-2 whitespace-pre-wrap break-words">
                    {line || ' '}
                  </pre>
                </div>
              );
            })}
          </div>
        </div>

        {/* Footer */}
        <div className="px-4 py-2 border-t border-gray-200 bg-gray-50 text-sm text-gray-500">
          {document.total_lines} lines • {document.file_type || 'text'} • 
          Created {new Date(document.created_at).toLocaleDateString()}
        </div>
      </div>
    </div>
  );
}

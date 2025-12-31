import React, { useState, useEffect, useRef } from 'react';
import { Send, Loader2, ExternalLink, FileText, Settings2, Eye } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { tomorrow } from 'react-syntax-highlighter/dist/esm/styles/prism';
import { api, ChatSession, ChatMessage, RAGTechnique, CitationSource } from '../services/api';
import { DocumentViewer } from './DocumentViewer';

const RAG_TECHNIQUES: { value: RAGTechnique; label: string; description: string }[] = [
  { value: 'standard', label: 'Standard', description: 'Basic retrieval-augmented generation' },
  { value: 'rag_fusion', label: 'RAG Fusion', description: 'Multiple query variations for better retrieval' },
  { value: 'hyde', label: 'HyDE', description: 'Hypothetical document embeddings' },
  { value: 'multi_query', label: 'Multi-Query', description: 'Multiple perspectives for comprehensive search' },
];

interface ChatInterfaceProps {
  session: ChatSession;
  workspaceId: number;
}

export function ChatInterface({ session, workspaceId }: ChatInterfaceProps) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [inputMessage, setInputMessage] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');
  const [selectedTechnique, setSelectedTechnique] = useState<RAGTechnique>('standard');
  const [showTechniqueSelector, setShowTechniqueSelector] = useState(false);
  const [viewingDocument, setViewingDocument] = useState<{
    documentId: number;
    chunkId?: number;
    startLine?: number;
    endLine?: number;
  } | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    loadChatHistory();
  }, [session.id]);

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const loadChatHistory = async () => {
    try {
      const history = await api.getChatHistory(session.id);
      setMessages(history.messages);
    } catch (err) {
      console.error('Failed to load chat history:', err);
      setError('Failed to load chat history');
    }
  };

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  const handleSendMessage = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!inputMessage.trim() || isLoading) return;

    const userMessage = inputMessage.trim();
    setInputMessage('');
    setIsLoading(true);
    setError('');

    // Add user message to UI immediately
    const tempUserMessage: ChatMessage = {
      id: Date.now(),
      role: 'user',
      content: userMessage,
      created_at: new Date().toISOString(),
    };
    setMessages(prev => [...prev, tempUserMessage]);

    try {
      const response = await api.sendChatMessage(session.id, userMessage, selectedTechnique);
      
      // Add assistant response
      const assistantMessage: ChatMessage = {
        id: response.message_id,
        role: 'assistant',
        content: response.answer,
        metadata: {
          sources: response.sources,
          context_used: response.context_used,
          technique: response.technique,
        },
        created_at: new Date().toISOString(),
      };

      setMessages(prev => [...prev.slice(0, -1), tempUserMessage, assistantMessage]);
    } catch (err) {
      console.error('Failed to send message:', err);
      setError('Failed to send message. Please try again.');
      // Remove the temporary user message on error
      setMessages(prev => prev.slice(0, -1));
    } finally {
      setIsLoading(false);
    }
  };

  const renderMessage = (message: ChatMessage) => {
    if (message.role === 'user') {
      return (
        <div key={message.id} className="flex justify-end mb-4">
          <div className="max-w-3xl bg-primary-600 text-white rounded-lg px-4 py-2">
            <p className="whitespace-pre-wrap">{message.content}</p>
          </div>
        </div>
      );
    }

    return (
      <div key={message.id} className="flex justify-start mb-4">
        <div className="max-w-4xl bg-white border border-gray-200 rounded-lg px-4 py-3">
          <div className="prose prose-sm max-w-none prose-table:border-collapse prose-table:w-full prose-th:border prose-th:border-gray-300 prose-th:bg-gray-100 prose-th:px-3 prose-th:py-2 prose-td:border prose-td:border-gray-300 prose-td:px-3 prose-td:py-2">
            <ReactMarkdown
              remarkPlugins={[remarkGfm]}
              components={{
                code({ className, children, ...props }: any) {
                  const match = /language-(\w+)/.exec(className || '');
                  const isInline = !match;
                  
                  return !isInline ? (
                    <SyntaxHighlighter
                      style={tomorrow as any}
                      language={match[1]}
                      PreTag="div"
                    >
                      {String(children).replace(/\n$/, '')}
                    </SyntaxHighlighter>
                  ) : (
                    <code className={className} {...props}>
                      {children}
                    </code>
                  );
                },
                table({ children, ...props }: any) {
                  return (
                    <div className="overflow-x-auto my-4">
                      <table className="min-w-full border-collapse border border-gray-300" {...props}>
                        {children}
                      </table>
                    </div>
                  );
                },
                thead({ children, ...props }: any) {
                  return <thead className="bg-gray-100" {...props}>{children}</thead>;
                },
                th({ children, ...props }: any) {
                  return (
                    <th className="border border-gray-300 px-3 py-2 text-left font-semibold text-gray-700" {...props}>
                      {children}
                    </th>
                  );
                },
                td({ children, ...props }: any) {
                  return (
                    <td className="border border-gray-300 px-3 py-2 text-gray-600" {...props}>
                      {children}
                    </td>
                  );
                },
                tr({ children, ...props }: any) {
                  return <tr className="hover:bg-gray-50" {...props}>{children}</tr>;
                },
              }}
            >
              {message.content}
            </ReactMarkdown>
          </div>
          
          {/* Sources */}
          {message.metadata?.sources && message.metadata.sources.length > 0 && (
            <div className="mt-4 pt-3 border-t border-gray-100">
              <p className="text-xs font-medium text-gray-600 mb-2">Sources:</p>
              <div className="space-y-1">
                {message.metadata.sources.map((source: CitationSource, index: number) => (
                  <div key={index} className="flex items-center space-x-2 text-xs group">
                    <FileText className="h-3 w-3 text-gray-400" />
                    <span className="text-gray-600 font-medium">{source.title}</span>
                    
                    {/* Line numbers */}
                    {source.start_line && source.end_line && (
                      <span className="text-gray-400">
                        (L{source.start_line}-{source.end_line})
                      </span>
                    )}
                    
                    {/* Page number for PDFs */}
                    {source.page_number && (
                      <span className="text-gray-400">
                        (Page {source.page_number})
                      </span>
                    )}
                    
                    {/* View document button */}
                    {source.document_id && (
                      <button
                        onClick={() => setViewingDocument({
                          documentId: source.document_id!,
                          chunkId: source.chunk_id,
                          startLine: source.start_line,
                          endLine: source.end_line
                        })}
                        className="flex items-center space-x-1 text-primary-600 hover:text-primary-700 opacity-0 group-hover:opacity-100 transition-opacity"
                        title="View source document"
                      >
                        <Eye className="h-3 w-3" />
                        <span>View</span>
                      </button>
                    )}
                    
                    {/* External links */}
                    {source.repo_url && (
                      <a
                        href={source.repo_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-primary-600 hover:text-primary-500"
                        title="Open repository"
                      >
                        <ExternalLink className="h-3 w-3" />
                      </a>
                    )}
                    {source.page_url && (
                      <a
                        href={source.page_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-primary-600 hover:text-primary-500"
                        title="Open page"
                      >
                        <ExternalLink className="h-3 w-3" />
                      </a>
                    )}
                    
                    <span className="text-gray-400">({source.score?.toFixed(2)})</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    );
  };

  return (
    <div className="flex flex-col h-full">
      {/* Chat Header */}
      <div className="bg-white border-b border-gray-200 px-6 py-4">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-lg font-medium text-gray-900">{session.title}</h3>
            <p className="text-sm text-gray-500">
              Created {new Date(session.created_at).toLocaleDateString()}
            </p>
          </div>
          <div className="relative">
            <button
              onClick={() => setShowTechniqueSelector(!showTechniqueSelector)}
              className="flex items-center space-x-2 px-3 py-2 text-sm bg-gray-100 hover:bg-gray-200 rounded-lg transition-colors"
            >
              <Settings2 className="h-4 w-4 text-gray-600" />
              <span className="text-gray-700">{RAG_TECHNIQUES.find(t => t.value === selectedTechnique)?.label}</span>
            </button>
            {showTechniqueSelector && (
              <div className="absolute right-0 mt-2 w-64 bg-white border border-gray-200 rounded-lg shadow-lg z-10">
                <div className="p-2">
                  <p className="text-xs font-medium text-gray-500 px-2 py-1">RAG Technique</p>
                  {RAG_TECHNIQUES.map((technique) => (
                    <button
                      key={technique.value}
                      onClick={() => {
                        setSelectedTechnique(technique.value);
                        setShowTechniqueSelector(false);
                      }}
                      className={`w-full text-left px-3 py-2 rounded-md text-sm transition-colors ${
                        selectedTechnique === technique.value
                          ? 'bg-primary-100 text-primary-700'
                          : 'hover:bg-gray-100 text-gray-700'
                      }`}
                    >
                      <div className="font-medium">{technique.label}</div>
                      <div className="text-xs text-gray-500">{technique.description}</div>
                    </button>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-6 bg-gray-50">
        {messages.length === 0 ? (
          <div className="flex items-center justify-center h-full">
            <div className="text-center">
              <div className="w-16 h-16 bg-primary-100 rounded-full flex items-center justify-center mx-auto mb-4">
                <Send className="h-8 w-8 text-primary-600" />
              </div>
              <h3 className="text-lg font-medium text-gray-900 mb-2">
                Start the conversation
              </h3>
              <p className="text-gray-500 max-w-sm">
                Ask questions about your knowledge base. I'll search through your documents and provide relevant answers.
              </p>
            </div>
          </div>
        ) : (
          <div className="max-w-4xl mx-auto">
            {messages.map(renderMessage)}
            {isLoading && (
              <div className="flex justify-start mb-4">
                <div className="bg-white border border-gray-200 rounded-lg px-4 py-3">
                  <div className="flex items-center space-x-2">
                    <Loader2 className="h-4 w-4 animate-spin text-primary-600" />
                    <span className="text-sm text-gray-600">Thinking...</span>
                  </div>
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>
        )}
      </div>

      {/* Input */}
      <div className="bg-white border-t border-gray-200 p-4">
        {error && (
          <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-md">
            <p className="text-sm text-red-600">{error}</p>
          </div>
        )}
        
        <form onSubmit={handleSendMessage} className="max-w-4xl mx-auto">
          <div className="flex space-x-4">
            <div className="flex-1">
              <textarea
                value={inputMessage}
                onChange={(e) => setInputMessage(e.target.value)}
                placeholder="Ask a question about your knowledge base..."
                className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500 resize-none"
                rows={3}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault();
                    handleSendMessage(e);
                  }
                }}
              />
            </div>
            <button
              type="submit"
              disabled={!inputMessage.trim() || isLoading}
              className="px-6 py-3 bg-primary-600 text-white rounded-lg hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500 disabled:opacity-50 disabled:cursor-not-allowed flex items-center"
            >
              {isLoading ? (
                <Loader2 className="h-5 w-5 animate-spin" />
              ) : (
                <Send className="h-5 w-5" />
              )}
            </button>
          </div>
          <div className="flex items-center justify-between mt-2">
            <p className="text-xs text-gray-500">
              Press Enter to send, Shift+Enter for new line
            </p>
            <p className="text-xs text-gray-500">
              Using: <span className="font-medium text-primary-600">{RAG_TECHNIQUES.find(t => t.value === selectedTechnique)?.label}</span>
            </p>
          </div>
        </form>
      </div>

      {/* Document Viewer Modal */}
      {viewingDocument && (
        <DocumentViewer
          documentId={viewingDocument.documentId}
          chunkId={viewingDocument.chunkId}
          startLine={viewingDocument.startLine}
          endLine={viewingDocument.endLine}
          onClose={() => setViewingDocument(null)}
        />
      )}
    </div>
  );
}

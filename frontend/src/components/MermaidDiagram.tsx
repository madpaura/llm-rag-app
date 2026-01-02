import React, { useEffect, useRef, useState, useCallback } from 'react';
import mermaid from 'mermaid';
import { 
  Maximize2, 
  X, 
  ZoomIn, 
  ZoomOut, 
  RotateCcw, 
  ExternalLink, 
  Download, 
  Copy, 
  Check,
  Move
} from 'lucide-react';

// Initialize mermaid with default config
mermaid.initialize({
  startOnLoad: false,
  theme: 'default',
  securityLevel: 'loose',
  flowchart: {
    useMaxWidth: true,
    htmlLabels: true,
    curve: 'basis',
  },
  sequence: {
    useMaxWidth: true,
    diagramMarginX: 50,
    diagramMarginY: 10,
    actorMargin: 50,
    width: 150,
    height: 65,
    boxMargin: 10,
    boxTextMargin: 5,
    noteMargin: 10,
    messageMargin: 35,
  },
});

/**
 * Sanitize mermaid chart to handle special characters and LLM artifacts.
 * - Removes source citations like 【Source 1】 or [Source 1] that LLMs add
 * - Handles special characters in node labels
 */
function sanitizeMermaidChart(chart: string): string {
  // First, remove LLM source citations that break mermaid parsing
  let sanitized = chart
    // Remove Chinese bracket citations: 【Source 1】, 【Source 2】
    .replace(/【[^】]*】/g, '')
    // Remove bracket citations: [Source 1], [Source 2]  
    .replace(/\[Source\s*\d+\]/gi, '')
    // Remove parenthesis citations: (Source 1)
    .replace(/\(Source\s*\d+\)/gi, '')
    // Clean up any double spaces left behind
    .replace(/  +/g, ' ')
    // Clean up empty lines
    .replace(/^\s*[\r\n]/gm, '\n');

  // Handle special characters in flowchart node labels
  sanitized = sanitized.replace(
    /(\w+)\[([^\]]*)\]/g,
    (match, nodeId, label) => {
      // If label contains parentheses or other special chars, wrap in quotes
      if (/[(){}|<>]/.test(label)) {
        // Escape any existing quotes in the label
        const escapedLabel = label.replace(/"/g, '#quot;');
        return `${nodeId}["${escapedLabel}"]`;
      }
      return match;
    }
  ).replace(
    /(\w+)\{([^}]*)\}/g,
    (match, nodeId, label) => {
      // Same for diamond/decision nodes
      if (/[()[\]|<>]/.test(label)) {
        const escapedLabel = label.replace(/"/g, '#quot;');
        return `${nodeId}{"${escapedLabel}"}`;
      }
      return match;
    }
  );
  
  return sanitized;
}

interface MermaidDiagramProps {
  chart: string;
}

export function MermaidDiagram({ chart }: MermaidDiagramProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [svg, setSvg] = useState<string>('');
  const [error, setError] = useState<string | null>(null);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [zoom, setZoom] = useState(1);
  const [pan, setPan] = useState({ x: 0, y: 0 });
  const [isDragging, setIsDragging] = useState(false);
  const [dragStart, setDragStart] = useState({ x: 0, y: 0 });
  const [copied, setCopied] = useState(false);
  const modalContentRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const renderDiagram = async () => {
      if (!chart.trim()) return;

      try {
        // Generate unique ID for this diagram
        const id = `mermaid-${Math.random().toString(36).substr(2, 9)}`;
        
        // Sanitize the chart to handle special characters in labels
        const sanitizedChart = sanitizeMermaidChart(chart.trim());
        
        // Render the mermaid diagram
        const { svg: renderedSvg } = await mermaid.render(id, sanitizedChart);
        setSvg(renderedSvg);
        setError(null);
      } catch (err) {
        console.error('Mermaid rendering error:', err);
        setError(err instanceof Error ? err.message : 'Failed to render diagram');
      }
    };

    renderDiagram();
  }, [chart]);

  // Handle ESC key to close modal
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && isModalOpen) {
        setIsModalOpen(false);
        resetView();
      }
    };

    if (isModalOpen) {
      document.addEventListener('keydown', handleKeyDown);
      document.body.style.overflow = 'hidden';
    }

    return () => {
      document.removeEventListener('keydown', handleKeyDown);
      document.body.style.overflow = 'unset';
    };
  }, [isModalOpen]);

  const resetView = () => {
    setZoom(1);
    setPan({ x: 0, y: 0 });
  };

  const handleZoomIn = () => {
    setZoom(prev => Math.min(prev + 0.25, 3));
  };

  const handleZoomOut = () => {
    setZoom(prev => Math.max(prev - 0.25, 0.25));
  };

  const handleMouseDown = (e: React.MouseEvent) => {
    if (e.button === 0) {
      setIsDragging(true);
      setDragStart({ x: e.clientX - pan.x, y: e.clientY - pan.y });
    }
  };

  const handleMouseMove = (e: React.MouseEvent) => {
    if (isDragging) {
      setPan({
        x: e.clientX - dragStart.x,
        y: e.clientY - dragStart.y,
      });
    }
  };

  const handleMouseUp = () => {
    setIsDragging(false);
  };

  const handleWheel = (e: React.WheelEvent) => {
    e.preventDefault();
    const delta = e.deltaY > 0 ? -0.1 : 0.1;
    setZoom(prev => Math.max(0.25, Math.min(3, prev + delta)));
  };

  const openInNewTab = useCallback(() => {
    const blob = new Blob([svg], { type: 'image/svg+xml' });
    const url = URL.createObjectURL(blob);
    window.open(url, '_blank');
  }, [svg]);

  const saveAsPng = useCallback(async () => {
    if (!svg) return;

    // Create a canvas to convert SVG to PNG
    const canvas = document.createElement('canvas');
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const img = new Image();
    const svgBlob = new Blob([svg], { type: 'image/svg+xml;charset=utf-8' });
    const url = URL.createObjectURL(svgBlob);

    img.onload = () => {
      // Set canvas size with higher resolution for better quality
      const scale = 2;
      canvas.width = img.width * scale;
      canvas.height = img.height * scale;
      
      // Fill white background
      ctx.fillStyle = 'white';
      ctx.fillRect(0, 0, canvas.width, canvas.height);
      
      // Draw the image
      ctx.scale(scale, scale);
      ctx.drawImage(img, 0, 0);
      
      // Download
      const pngUrl = canvas.toDataURL('image/png');
      const link = document.createElement('a');
      link.download = 'mermaid-diagram.png';
      link.href = pngUrl;
      link.click();
      
      URL.revokeObjectURL(url);
    };

    img.src = url;
  }, [svg]);

  const copyCode = useCallback(() => {
    // Use fallback method for better compatibility
    const textArea = document.createElement('textarea');
    textArea.value = chart;
    textArea.style.position = 'fixed';
    textArea.style.left = '-9999px';
    textArea.style.top = '-9999px';
    document.body.appendChild(textArea);
    textArea.focus();
    textArea.select();
    
    try {
      document.execCommand('copy');
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.error('Failed to copy:', err);
    } finally {
      document.body.removeChild(textArea);
    }
  }, [chart]);

  if (error) {
    return (
      <div className="my-4 p-4 bg-red-50 border border-red-200 rounded-lg">
        <p className="text-sm text-red-600 font-medium">Failed to render diagram</p>
        <pre className="mt-2 text-xs text-red-500 overflow-x-auto">{chart}</pre>
      </div>
    );
  }

  return (
    <>
      {/* Inline diagram with click to expand */}
      <div
        ref={containerRef}
        className="my-4 p-4 bg-white border border-gray-200 rounded-lg overflow-x-auto relative group cursor-pointer"
        onClick={() => setIsModalOpen(true)}
      >
        <div dangerouslySetInnerHTML={{ __html: svg }} />
        
        {/* Hover hint - positioned at bottom, doesn't block diagram */}
        <div className="absolute bottom-2 left-1/2 transform -translate-x-1/2 opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none">
          <div className="bg-gray-800 bg-opacity-75 text-white px-3 py-1.5 rounded-lg flex items-center space-x-2 text-sm">
            <Maximize2 className="h-4 w-4" />
            <span>Click to expand</span>
          </div>
        </div>
      </div>

      {/* Modal */}
      {isModalOpen && (
        <div 
          className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50"
          onClick={(e) => {
            if (e.target === e.currentTarget) {
              setIsModalOpen(false);
              resetView();
            }
          }}
        >
          <div className="bg-white rounded-xl shadow-2xl w-[90vw] h-[90vh] flex flex-col">
            {/* Modal Header */}
            <div className="flex items-center justify-between px-4 py-3 border-b border-gray-200">
              <div className="flex items-center space-x-2">
                <span className="text-sm font-medium text-gray-700">Mermaid Diagram</span>
                <span className="text-xs text-gray-400">({Math.round(zoom * 100)}%)</span>
              </div>
              
              {/* Toolbar */}
              <div className="flex items-center space-x-1">
                {/* Zoom controls */}
                <button
                  onClick={handleZoomOut}
                  className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
                  title="Zoom out"
                >
                  <ZoomOut className="h-4 w-4 text-gray-600" />
                </button>
                <button
                  onClick={handleZoomIn}
                  className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
                  title="Zoom in"
                >
                  <ZoomIn className="h-4 w-4 text-gray-600" />
                </button>
                <button
                  onClick={resetView}
                  className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
                  title="Reset view"
                >
                  <RotateCcw className="h-4 w-4 text-gray-600" />
                </button>
                
                <div className="w-px h-6 bg-gray-200 mx-2" />
                
                {/* Actions */}
                <button
                  onClick={openInNewTab}
                  className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
                  title="Open in new tab"
                >
                  <ExternalLink className="h-4 w-4 text-gray-600" />
                </button>
                <button
                  onClick={saveAsPng}
                  className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
                  title="Save as PNG"
                >
                  <Download className="h-4 w-4 text-gray-600" />
                </button>
                <button
                  onClick={copyCode}
                  className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
                  title="Copy mermaid code"
                >
                  {copied ? (
                    <Check className="h-4 w-4 text-green-600" />
                  ) : (
                    <Copy className="h-4 w-4 text-gray-600" />
                  )}
                </button>
                
                <div className="w-px h-6 bg-gray-200 mx-2" />
                
                {/* Close */}
                <button
                  onClick={() => {
                    setIsModalOpen(false);
                    resetView();
                  }}
                  className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
                  title="Close (ESC)"
                >
                  <X className="h-4 w-4 text-gray-600" />
                </button>
              </div>
            </div>
            
            {/* Diagram area */}
            <div 
              ref={modalContentRef}
              className="flex-1 overflow-hidden bg-gray-50 relative"
              onMouseDown={handleMouseDown}
              onMouseMove={handleMouseMove}
              onMouseUp={handleMouseUp}
              onMouseLeave={handleMouseUp}
              onWheel={handleWheel}
              style={{ cursor: isDragging ? 'grabbing' : 'grab' }}
            >
              <div
                className="absolute inset-0 flex items-center justify-center"
                style={{
                  transform: `translate(${pan.x}px, ${pan.y}px) scale(${zoom})`,
                  transformOrigin: 'center center',
                  transition: isDragging ? 'none' : 'transform 0.1s ease-out',
                }}
              >
                <div 
                  className="bg-white p-8 rounded-lg shadow-sm"
                  dangerouslySetInnerHTML={{ __html: svg }} 
                />
              </div>
              
              {/* Pan hint */}
              <div className="absolute bottom-4 left-4 flex items-center space-x-2 text-xs text-gray-400 bg-white px-2 py-1 rounded shadow-sm">
                <Move className="h-3 w-3" />
                <span>Drag to pan • Scroll to zoom • ESC to close</span>
              </div>
            </div>
          </div>
        </div>
      )}
    </>
  );
}

import React from 'react';
import { Settings, Eye, ToggleLeft, ToggleRight } from 'lucide-react';
import { useConfig } from '../contexts/ConfigContext';

export function SettingsPage() {
  const { features, updateFeature } = useConfig();

  return (
    <div className="p-6 max-w-4xl mx-auto">
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
          <Settings className="h-6 w-6" />
          Settings
        </h1>
        <p className="text-gray-600 mt-1">Configure application features and preferences</p>
      </div>

      {/* Feature Flags Section */}
      <div className="bg-white rounded-lg shadow p-6">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">Feature Flags</h2>
        <p className="text-sm text-gray-600 mb-6">
          Enable or disable experimental features. These settings are stored locally in your browser.
        </p>

        <div className="space-y-4">
          {/* Embeddings Viewer Toggle */}
          <div className="flex items-center justify-between p-4 bg-gray-50 rounded-lg">
            <div className="flex items-start gap-3">
              <div className="p-2 bg-primary-100 rounded-lg">
                <Eye className="h-5 w-5 text-primary-600" />
              </div>
              <div>
                <h3 className="font-medium text-gray-900">Embeddings Viewer</h3>
                <p className="text-sm text-gray-600 mt-0.5">
                  View and navigate vector embeddings for your codebase. Useful for understanding 
                  how documents are chunked and embedded.
                </p>
              </div>
            </div>
            <button
              onClick={() => updateFeature('embeddingsViewer', !features.embeddingsViewer)}
              className={`flex-shrink-0 p-1 rounded-full transition-colors ${
                features.embeddingsViewer 
                  ? 'text-primary-600 hover:text-primary-700' 
                  : 'text-gray-400 hover:text-gray-500'
              }`}
              title={features.embeddingsViewer ? 'Disable feature' : 'Enable feature'}
            >
              {features.embeddingsViewer ? (
                <ToggleRight className="h-8 w-8" />
              ) : (
                <ToggleLeft className="h-8 w-8" />
              )}
            </button>
          </div>
        </div>
      </div>

      {/* Info Section */}
      <div className="mt-6 p-4 bg-blue-50 rounded-lg border border-blue-200">
        <p className="text-sm text-blue-800">
          <strong>Note:</strong> Feature flags are stored in your browser's local storage. 
          Clearing your browser data will reset these settings to their defaults.
        </p>
      </div>
    </div>
  );
}

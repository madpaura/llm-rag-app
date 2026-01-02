import React from 'react';
import { useParams, Navigate } from 'react-router-dom';
import { EmbeddingsViewer } from '../components/EmbeddingsViewer';
import { useConfig } from '../contexts/ConfigContext';

export function EmbeddingsPage() {
  const { workspaceId } = useParams<{ workspaceId: string }>();
  const { isFeatureEnabled } = useConfig();

  // Redirect if feature is not enabled
  if (!isFeatureEnabled('embeddingsViewer')) {
    return <Navigate to={`/workspace/${workspaceId}`} replace />;
  }

  return (
    <div className="h-full">
      <EmbeddingsViewer />
    </div>
  );
}

import React from 'react';
import { useParams, Navigate } from 'react-router-dom';
import { EmbeddingsViewer } from '../components/EmbeddingsViewer';
import { useConfig } from '../contexts/ConfigContext';
import { useAuth } from '../contexts/AuthContext';

export function EmbeddingsPage() {
  const { workspaceId } = useParams<{ workspaceId: string }>();
  const { isFeatureEnabled } = useConfig();
  const { user } = useAuth();

  // Redirect if feature is not enabled
  if (!isFeatureEnabled('embeddingsViewer')) {
    return <Navigate to={`/workspace/${workspaceId}`} replace />;
  }

  // Redirect if user doesn't have permission (unless admin)
  const hasPermission = user?.is_admin || user?.permissions?.can_view_embeddings;
  if (!hasPermission) {
    return <Navigate to={`/workspace/${workspaceId}`} replace />;
  }

  return (
    <div className="h-full">
      <EmbeddingsViewer />
    </div>
  );
}

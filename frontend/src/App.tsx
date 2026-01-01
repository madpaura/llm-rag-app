import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider } from './contexts/AuthContext';
import { Layout } from './components/Layout';
import { Login } from './pages/Login';
import { Dashboard } from './pages/Dashboard';
import { WorkspaceView } from './pages/WorkspaceView';
import { IngestionPage } from './pages/IngestionPage';
import { ProtectedRoute } from './components/ProtectedRoute';
import './App.css';

// Base path for the application (used when hosted under a subpath like /rag/ui)
// Detect if we're behind nginx proxy by checking the URL path
const getBasename = () => {
  // Check if accessed via /rag/ui path (nginx proxy)
  if (window.location.pathname.startsWith('/rag/ui')) {
    return '/rag/ui';
  }
  // Use PUBLIC_URL for production builds, empty for local dev
  return process.env.PUBLIC_URL || '';
};

const basename = getBasename();

function App() {
  return (
    <AuthProvider>
      <Router basename={basename}>
        <div className="App">
          <Routes>
            <Route path="/login" element={<Login />} />
            <Route
              path="/"
              element={
                <ProtectedRoute>
                  <Layout />
                </ProtectedRoute>
              }
            >
              <Route index element={<Navigate to="/dashboard" replace />} />
              <Route path="dashboard" element={<Dashboard />} />
              <Route path="workspace/:workspaceId" element={<WorkspaceView />} />
              <Route path="workspace/:workspaceId/ingest" element={<IngestionPage />} />
            </Route>
          </Routes>
        </div>
      </Router>
    </AuthProvider>
  );
}

export default App;

import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';

interface FeatureFlags {
  embeddingsViewer: boolean;
}

interface ConfigContextType {
  features: FeatureFlags;
  updateFeature: (feature: keyof FeatureFlags, enabled: boolean) => void;
  isFeatureEnabled: (feature: keyof FeatureFlags) => boolean;
}

const defaultFeatures: FeatureFlags = {
  embeddingsViewer: false,
};

const ConfigContext = createContext<ConfigContextType | undefined>(undefined);

const CONFIG_STORAGE_KEY = 'rag_app_config';

export function ConfigProvider({ children }: { children: ReactNode }) {
  const [features, setFeatures] = useState<FeatureFlags>(() => {
    const saved = localStorage.getItem(CONFIG_STORAGE_KEY);
    if (saved) {
      try {
        return { ...defaultFeatures, ...JSON.parse(saved) };
      } catch {
        return defaultFeatures;
      }
    }
    return defaultFeatures;
  });

  useEffect(() => {
    localStorage.setItem(CONFIG_STORAGE_KEY, JSON.stringify(features));
  }, [features]);

  const updateFeature = (feature: keyof FeatureFlags, enabled: boolean) => {
    setFeatures(prev => ({ ...prev, [feature]: enabled }));
  };

  const isFeatureEnabled = (feature: keyof FeatureFlags) => {
    return features[feature] ?? false;
  };

  return (
    <ConfigContext.Provider value={{ features, updateFeature, isFeatureEnabled }}>
      {children}
    </ConfigContext.Provider>
  );
}

export function useConfig() {
  const context = useContext(ConfigContext);
  if (context === undefined) {
    throw new Error('useConfig must be used within a ConfigProvider');
  }
  return context;
}

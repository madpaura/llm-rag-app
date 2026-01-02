/**
 * Custom hook for caching form data in localStorage.
 * Persists form fields so users don't have to re-enter them.
 */
import { useState, useEffect, useCallback } from 'react';

const CACHE_PREFIX = 'rag_form_cache_';
const CACHE_EXPIRY_DAYS = 30;

interface CacheEntry<T> {
  data: T;
  timestamp: number;
}

/**
 * Hook to cache form data in localStorage with automatic expiry.
 * Sensitive fields (like tokens) are excluded from caching.
 * 
 * @param formKey - Unique key for this form (e.g., 'git_ingestion')
 * @param initialState - Initial form state
 * @param sensitiveFields - Array of field names to exclude from caching
 */
export function useFormCache<T extends Record<string, any>>(
  formKey: string,
  initialState: T,
  sensitiveFields: (keyof T)[] = []
): [T, React.Dispatch<React.SetStateAction<T>>, () => void] {
  const cacheKey = `${CACHE_PREFIX}${formKey}`;
  
  // Initialize state from cache or initial state
  const [formData, setFormData] = useState<T>(() => {
    try {
      const cached = localStorage.getItem(cacheKey);
      if (cached) {
        const entry: CacheEntry<Partial<T>> = JSON.parse(cached);
        
        // Check if cache is expired
        const expiryTime = CACHE_EXPIRY_DAYS * 24 * 60 * 60 * 1000;
        if (Date.now() - entry.timestamp > expiryTime) {
          localStorage.removeItem(cacheKey);
          return initialState;
        }
        
        // Merge cached data with initial state (to handle new fields)
        return { ...initialState, ...entry.data };
      }
    } catch (e) {
      console.warn('Failed to load form cache:', e);
    }
    return initialState;
  });
  
  // Save to cache whenever form data changes
  useEffect(() => {
    try {
      // Filter out sensitive fields before caching
      const dataToCache: Partial<T> = { ...formData };
      sensitiveFields.forEach(field => {
        delete dataToCache[field];
      });
      
      // Also don't cache file inputs or empty values
      Object.keys(dataToCache).forEach(key => {
        const value = dataToCache[key as keyof T] as unknown;
        // Check for File objects
        if (typeof value === 'object' && value !== null) {
          if ((value as object).constructor?.name === 'File' || 
              (value as object).constructor?.name === 'FileList' ||
              (Array.isArray(value) && value.length > 0 && 
               typeof value[0] === 'object' && value[0]?.constructor?.name === 'File')) {
            delete dataToCache[key as keyof T];
          }
        }
      });
      
      const entry: CacheEntry<Partial<T>> = {
        data: dataToCache,
        timestamp: Date.now()
      };
      
      localStorage.setItem(cacheKey, JSON.stringify(entry));
    } catch (e) {
      console.warn('Failed to save form cache:', e);
    }
  }, [formData, cacheKey, sensitiveFields]);
  
  // Clear cache function
  const clearCache = useCallback(() => {
    try {
      localStorage.removeItem(cacheKey);
    } catch (e) {
      console.warn('Failed to clear form cache:', e);
    }
  }, [cacheKey]);
  
  return [formData, setFormData, clearCache];
}

/**
 * Clear all form caches
 */
export function clearAllFormCaches(): void {
  try {
    const keysToRemove: string[] = [];
    for (let i = 0; i < localStorage.length; i++) {
      const key = localStorage.key(i);
      if (key && key.startsWith(CACHE_PREFIX)) {
        keysToRemove.push(key);
      }
    }
    keysToRemove.forEach(key => localStorage.removeItem(key));
  } catch (e) {
    console.warn('Failed to clear all form caches:', e);
  }
}

import { useState, useEffect } from 'react';
import { Script } from '../types';

interface UseScriptResult {
  script: Script | undefined;
  isLoading: boolean;
  error: Error | undefined;
  mutate: () => Promise<void>;
}

export function useScript(id?: number): UseScriptResult {
  const [script, setScript] = useState<Script>();
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<Error>();

  const fetchScript = async () => {
    if (!id) {
      setScript(undefined);
      setIsLoading(false);
      setError(undefined);
      return;
    }
    
    setIsLoading(true);
    setError(undefined);
    
    try {
      const response = await fetch(`/api/scripts/${id}`);
      if (!response.ok) {
        throw new Error(`Failed to fetch script: ${response.statusText}`);
      }
      const data = await response.json();
      setScript(data);
    } catch (err) {
      setError(err instanceof Error ? err : new Error('Failed to fetch script'));
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchScript();
  }, [id]);

  return {
    script,
    isLoading,
    error,
    mutate: fetchScript,
  };
} 
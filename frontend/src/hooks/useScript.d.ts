import { Script } from '../types';

interface UseScriptResult {
  script: Script | undefined;
  isLoading: boolean;
  error: Error | undefined;
  mutate: () => Promise<void>;
}

export declare function useScript(id?: number): UseScriptResult; 
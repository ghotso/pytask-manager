interface UseWebSocketResult {
  connect: (path: string) => void;
  onMessage: (handler: (message: string) => void) => void;
  onClose: (handler: () => void) => void;
  send: (message: string) => void;
  close: () => void;
}

export declare function useWebSocket(): UseWebSocketResult; 
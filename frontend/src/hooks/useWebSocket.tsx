import { useRef, useCallback } from 'react';

interface UseWebSocketResult {
  connect: (path: string) => void;
  onMessage: (handler: (message: string) => void) => void;
  onClose: (handler: () => void) => void;
  send: (message: string) => void;
  close: () => void;
}

export function useWebSocket(): UseWebSocketResult {
  const wsRef = useRef<WebSocket>();
  const messageHandlerRef = useRef<(message: string) => void>();
  const closeHandlerRef = useRef<() => void>();

  const connect = useCallback((path: string) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.close();
    }

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}${path}`;
    
    const ws = new WebSocket(wsUrl);
    
    ws.onmessage = (event) => {
      messageHandlerRef.current?.(event.data);
    };
    
    ws.onclose = () => {
      closeHandlerRef.current?.();
    };
    
    wsRef.current = ws;
  }, []);

  const onMessage = useCallback((handler: (message: string) => void) => {
    messageHandlerRef.current = handler;
  }, []);

  const onClose = useCallback((handler: () => void) => {
    closeHandlerRef.current = handler;
  }, []);

  const send = useCallback((message: string) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(message);
    }
  }, []);

  const close = useCallback(() => {
    wsRef.current?.close();
  }, []);

  return {
    connect,
    onMessage,
    onClose,
    send,
    close,
  };
} 
import { useCallback, useRef } from 'react';

export function useWebSocket() {
  const wsRef = useRef<WebSocket | null>(null);
  
  const connect = useCallback((path: string) => {
    // Close existing connection if any
    if (wsRef.current) {
      wsRef.current.close();
    }
    
    // Create new WebSocket connection
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}${path}`;
    wsRef.current = new WebSocket(wsUrl);
    
    // Set up error handler
    wsRef.current.onerror = (error) => {
      console.error('WebSocket error:', error);
    };
  }, []);
  
  const onMessage = useCallback((handler: (message: string) => void) => {
    if (!wsRef.current) return;
    
    wsRef.current.onmessage = (event) => {
      handler(event.data);
    };
  }, []);
  
  const onClose = useCallback((handler: () => void) => {
    if (!wsRef.current) return;
    
    wsRef.current.onclose = () => {
      handler();
      wsRef.current = null;
    };
  }, []);
  
  const send = useCallback((message: string) => {
    if (!wsRef.current) return;
    
    wsRef.current.send(message);
  }, []);
  
  const close = useCallback(() => {
    if (!wsRef.current) return;
    
    wsRef.current.close();
    wsRef.current = null;
  }, []);
  
  return {
    connect,
    onMessage,
    onClose,
    send,
    close,
  };
} 
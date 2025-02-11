import { Button, Group, Paper, Stack, Text, Title } from '@mantine/core';
import { notifications } from '@mantine/notifications';
import { IconPlayerPlay } from '@tabler/icons-react';
import { useEffect, useRef, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { Script, scriptsApi } from '../api/client';

export function ScriptExecution() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [script, setScript] = useState<Script | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isExecuting, setIsExecuting] = useState(false);
  const [output, setOutput] = useState<string[]>([]);
  const outputRef = useRef<HTMLDivElement>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const reconnectAttemptsRef = useRef(0);
  const MAX_RECONNECT_ATTEMPTS = 5;
  const [hasFinished, setHasFinished] = useState(false);
  const [isConnected, setIsConnected] = useState(false);

  useEffect(() => {
    if (id) {
      loadScript(parseInt(id));
    }
    return () => {
      cleanupWebSocket();
    };
  }, [id]);

  useEffect(() => {
    if (outputRef.current) {
      outputRef.current.scrollTop = outputRef.current.scrollHeight;
    }
  }, [output]);

  const cleanupWebSocket = () => {
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }
    reconnectAttemptsRef.current = 0;
    setIsConnected(false);
  };

  const loadScript = async (scriptId: number) => {
    try {
      const data = await scriptsApi.get(scriptId);
      setScript(data);
    } catch (error) {
      notifications.show({
        title: 'Error',
        message: 'Failed to load script',
        color: 'red',
      });
      navigate('/');
    } finally {
      setIsLoading(false);
    }
  };

  const setupWebSocket = (scriptId: number) => {
    // Clean up any existing connection
    cleanupWebSocket();

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const ws = new WebSocket(`${protocol}//${window.location.host}/api/scripts/${scriptId}/ws`);
    wsRef.current = ws;

    ws.onopen = () => {
      console.log('WebSocket connected');
      reconnectAttemptsRef.current = 0;
      setIsConnected(true);
      if (!output.includes('Connecting to execution stream...')) {
        setOutput(current => [...current, 'Connecting to execution stream...']);
      }
    };

    ws.onmessage = (event) => {
      const message = event.data;
      console.log('Received message:', message);
      
      if (message === 'No running execution found') {
        setIsExecuting(false);
        setHasFinished(true);
        notifications.show({
          title: 'No Running Execution',
          message: 'The script execution has already completed.',
          color: 'blue',
        });
        return;
      }
      
      // Handle connection message
      if (message === 'Connected to execution stream...') {
        if (!output.includes('Connected to execution stream...')) {
          setOutput(current => [...current, message]);
        }
        return;
      }
      
      // Handle status updates
      if (message.startsWith('STATUS:')) {
        setOutput(current => [...current, message]);
        return;
      }
      
      // Handle execution finished message
      if (message === 'Execution finished.') {
        if (!hasFinished) {
          setOutput(current => [...current, message]);
          setIsExecuting(false);
          setHasFinished(true);
          cleanupWebSocket();
        }
        return;
      }
      
      // Handle all other messages
      setOutput(current => [...current, message]);
    };

    ws.onerror = (error) => {
      console.error('WebSocket error:', error);
      if (!hasFinished) {
        notifications.show({
          title: 'Connection Error',
          message: 'Error connecting to execution stream. Will try to reconnect...',
          color: 'yellow',
        });
      }
    };

    ws.onclose = (event) => {
      console.log('WebSocket closed:', event.code, event.reason);
      wsRef.current = null;
      setIsConnected(false);

      // Only attempt to reconnect if we're still executing, haven't finished, and it wasn't a normal closure
      if (isExecuting && !hasFinished && event.code !== 1000 && reconnectAttemptsRef.current < MAX_RECONNECT_ATTEMPTS) {
        const delay = Math.min(1000 * Math.pow(2, reconnectAttemptsRef.current), 10000);
        console.log(`Attempting to reconnect in ${delay}ms (attempt ${reconnectAttemptsRef.current + 1})`);
        
        setOutput(current => [...current, `Connection lost. Reconnecting in ${delay/1000} seconds...`]);
        
        reconnectTimeoutRef.current = setTimeout(() => {
          reconnectAttemptsRef.current++;
          setupWebSocket(scriptId);
        }, delay);
      } else if (reconnectAttemptsRef.current >= MAX_RECONNECT_ATTEMPTS && !hasFinished) {
        setIsExecuting(false);
        notifications.show({
          title: 'Connection Lost',
          message: 'Failed to maintain connection to execution stream. The script may still be running in the background.',
          color: 'red',
        });
      }
    };

    return ws;
  };

  const handleExecute = async () => {
    if (!id || !script) return;
    if (isExecuting) return; // Prevent multiple executions

    setIsExecuting(true);
    setHasFinished(false);
    setOutput([]);

    try {
      // First, start the execution via HTTP
      const { execution_id } = await scriptsApi.execute(parseInt(id));
      console.log('Execution started with ID:', execution_id);
      
      // Setup WebSocket connection with a small delay to ensure the backend is ready
      setTimeout(() => {
        setupWebSocket(parseInt(id));
      }, 500);
    } catch (error) {
      console.error('Failed to start execution:', error);
      notifications.show({
        title: 'Error',
        message: 'Failed to start script execution. Please check the execution history for details.',
        color: 'red',
      });
      setIsExecuting(false);
      setHasFinished(true);
      cleanupWebSocket();
    }
  };

  // Function to check if there are any uninstalled dependencies
  const hasUninstalledDependencies = (script: Script): boolean => {
    return script.dependencies.some(dep => !dep.installed_version);
  };

  if (isLoading || !script) {
    return null;
  }

  return (
    <Stack>
      <Group justify="space-between">
        <Stack gap={0}>
          <Title order={2}>Execute Script</Title>
          <Text c="dimmed">{script.name}</Text>
        </Stack>

        <Group>
          <Button
            variant="light"
            onClick={() => navigate('/')}
            disabled={isExecuting}
          >
            Back
          </Button>
          <Button
            onClick={handleExecute}
            disabled={isExecuting || hasUninstalledDependencies(script)}
            leftSection={<IconPlayerPlay size={14} />}
            color={hasUninstalledDependencies(script) ? 'red' : 'blue'}
            title={hasUninstalledDependencies(script) ? 'Please install all dependencies before running the script' : undefined}
          >
            {isExecuting ? 'Running...' : 'Run Script'}
          </Button>
        </Group>
      </Group>

      {hasUninstalledDependencies(script) && (
        <Paper p="md" bg="red.1" mb="md">
          <Text c="red" fw={500}>
            This script has uninstalled dependencies. Please install all dependencies before running the script.
          </Text>
        </Paper>
      )}

      <Paper
        ref={outputRef}
        withBorder
        p="md"
        style={{
          height: '500px',
          overflowY: 'auto',
          backgroundColor: '#1e1e1e',
        }}
      >
        {output.length > 0 ? (
          output.map((line, index) => (
            <Text
              key={index}
              style={{
                fontFamily: 'monospace',
                whiteSpace: 'pre-wrap',
                color: line.startsWith('STATUS:') ? '#4CAF50' : 
                       line.includes('Error:') ? '#f44336' : 
                       line.includes('Connection lost') ? '#ff9800' : 
                       '#d4d4d4',
              }}
            >
              {line}
            </Text>
          ))
        ) : (
          <Text c="dimmed" ta="center">
            {isExecuting 
              ? isConnected 
                ? 'Waiting for output...' 
                : 'Connecting to execution stream...'
              : 'Click Execute to run the script'
            }
          </Text>
        )}
      </Paper>
    </Stack>
  );
} 
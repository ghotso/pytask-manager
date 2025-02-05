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
  const executionIdRef = useRef<number | null>(null);

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
    executionIdRef.current = null;
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

  const setupWebSocket = (scriptId: number, executionId: number) => {
    // Clean up any existing connection
    cleanupWebSocket();

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const ws = new WebSocket(`${protocol}//${window.location.host}/api/scripts/${scriptId}/ws`);
    wsRef.current = ws;
    executionIdRef.current = executionId;

    ws.onopen = () => {
      console.log('WebSocket connected');
    };

    ws.onmessage = (event) => {
      setOutput((current) => [...current, event.data]);
    };

    ws.onerror = (error) => {
      console.error('WebSocket error:', error);
      notifications.show({
        title: 'Error',
        message: 'Failed to connect to execution stream',
        color: 'red',
      });
      setIsExecuting(false);
      cleanupWebSocket();
    };

    ws.onclose = () => {
      console.log('WebSocket closed');
      setIsExecuting(false);
      cleanupWebSocket();
    };

    return ws;
  };

  const handleExecute = async () => {
    if (!id || !script) return;
    if (isExecuting) return; // Prevent multiple executions

    setIsExecuting(true);
    setOutput([]);

    try {
      // First, start the execution via HTTP
      const { execution_id } = await scriptsApi.execute(parseInt(id));
      console.log('Execution started with ID:', execution_id);
      
      // Setup WebSocket connection
      setupWebSocket(parseInt(id), execution_id);
    } catch (error) {
      console.error('Failed to start execution:', error);
      notifications.show({
        title: 'Error',
        message: 'Failed to start script execution',
        color: 'red',
      });
      setIsExecuting(false);
      cleanupWebSocket();
    }
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
            disabled={isExecuting}
            leftSection={<IconPlayerPlay size={16} />}
          >
            {isExecuting ? 'Executing...' : 'Execute'}
          </Button>
        </Group>
      </Group>

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
                color: '#d4d4d4',
              }}
            >
              {line}
            </Text>
          ))
        ) : (
          <Text c="dimmed" ta="center">
            {isExecuting ? 'Waiting for output...' : 'Click Execute to run the script'}
          </Text>
        )}
      </Paper>
    </Stack>
  );
} 
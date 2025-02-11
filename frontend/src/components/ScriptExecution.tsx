import { Button, Group, Paper, Stack, Text, Title } from '@mantine/core';
import { notifications } from '@mantine/notifications';
import { IconPlayerPlay } from '@tabler/icons-react';
import { useEffect, useRef, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { Script, scriptsApi } from '../api/client';
import { ExecutionStatus } from '../types';
import { WS_BASE_URL } from '../config';
import { useScript } from '../hooks/useScript';

export function ScriptExecution() {
  const { id } = useParams();
  const navigate = useNavigate();
  const wsRef = useRef<WebSocket | null>(null);
  const { script, mutate } = useScript(id ? parseInt(id) : undefined);
  const [isLoading, setIsLoading] = useState(true);
  const [isExecuting, setIsExecuting] = useState(false);
  const [output, setOutput] = useState('');
  const outputRef = useRef<HTMLDivElement>(null);
  const [executionStatus, setExecutionStatus] = useState<ExecutionStatus>(ExecutionStatus.PENDING);

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
    setOutput('');
    setExecutionStatus(ExecutionStatus.PENDING);
  };

  const loadScript = async (scriptId: number) => {
    try {
      const data = await scriptsApi.get(scriptId);
      mutate(data);
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
    // Close existing connection if any
    cleanupWebSocket();
    
    const connectWebSocket = (retryCount = 0) => {
      // Create new WebSocket connection with execution ID
      const wsUrl = `${WS_BASE_URL}/api/scripts/${scriptId}/ws?execution_id=${executionId}`;
      wsRef.current = new WebSocket(wsUrl);
      
      wsRef.current.onopen = () => {
        console.log('WebSocket connected');
      };
      
      wsRef.current.onmessage = (event) => {
        const message = event.data;
        
        // Don't add error messages about execution ID to output
        if (message.includes('No execution ID provided') || message.includes('Execution not found')) {
          if (retryCount < 5) {
            console.log(`Retrying WebSocket connection (attempt ${retryCount + 1})...`);
            wsRef.current?.close();
            setTimeout(() => connectWebSocket(retryCount + 1), 1000);
          } else {
            setOutput(prev => prev + 'Error: Failed to connect to execution stream\n');
          }
          return;
        }
        
        setOutput(prev => prev + message + '\n');
        
        if (message.startsWith('STATUS:')) {
          const status = message.split(':')[1].trim();
          setExecutionStatus(status as ExecutionStatus);
          
          if (status === ExecutionStatus.SUCCESS || status === ExecutionStatus.FAILURE) {
            mutate();  // Refresh script data
            cleanupWebSocket();
          }
        }
      };
      
      wsRef.current.onerror = (error) => {
        console.error('WebSocket error:', error);
        if (retryCount < 5) {
          console.log(`Retrying WebSocket connection (attempt ${retryCount + 1})...`);
          setTimeout(() => connectWebSocket(retryCount + 1), 1000);
        } else {
          setOutput(prev => prev + 'Error: WebSocket connection failed after 5 attempts\n');
        }
      };
      
      wsRef.current.onclose = () => {
        console.log('WebSocket closed');
      };
    };
    
    // Add a longer initial delay to allow the execution to be created
    setTimeout(() => connectWebSocket(), 1000);
  };

  const handleExecute = async () => {
    if (!script || hasUninstalledDependencies(script)) {
      return;
    }
    
    setOutput('');
    setIsExecuting(true);
    setExecutionStatus(ExecutionStatus.PENDING);
    
    try {
      const response = await scriptsApi.execute(script.id);
      if (!response.execution_id) {
        throw new Error('No execution ID received from server');
      }
      console.log('Execution started:', response);
      
      // Set up WebSocket connection with execution ID
      setupWebSocket(script.id, response.execution_id);
      
    } catch (error) {
      console.error('Failed to execute script:', error);
      setOutput(prev => prev + `Error: ${error instanceof Error ? error.message : 'Failed to execute script'}\n`);
      setExecutionStatus(ExecutionStatus.FAILURE);
      setIsExecuting(false);
    }
  };

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
          <Text
            style={{
              fontFamily: 'monospace',
              whiteSpace: 'pre-wrap',
              color: executionStatus === ExecutionStatus.SUCCESS ? '#4CAF50' : 
                     executionStatus === ExecutionStatus.FAILURE ? '#f44336' : 
                     '#d4d4d4',
            }}
          >
            {output}
          </Text>
        ) : (
          <Text c="dimmed" ta="center">
            {isExecuting ? 'Waiting for output...' : 'Click Execute to run the script'}
          </Text>
        )}
      </Paper>
    </Stack>
  );
} 
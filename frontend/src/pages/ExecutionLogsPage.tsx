import { useEffect, useState } from 'react';
import { Card, Select, Text, Group, Badge, Box, Code, Stack, Title, LoadingOverlay, Button } from '@mantine/core';
import { useApi } from '../hooks/useApi';
import { Script, Execution, ExecutionStatus } from '../types';
import { useSearchParams } from 'react-router-dom';
import { 
  IconCheck,
  IconX,
  IconClock,
  IconLoader2,
} from '@tabler/icons-react';

interface ExtendedExecution extends Execution {
  scriptName: string;
}

export function ExecutionLogsPage() {
  const api = useApi();
  const [searchParams, setSearchParams] = useSearchParams();
  const [scripts, setScripts] = useState<Script[]>([]);
  const [executions, setExecutions] = useState<ExtendedExecution[]>([]);
  const [selectedScript, setSelectedScript] = useState<string | null>(searchParams.get('script'));
  const [isLoading, setIsLoading] = useState(true);
  const [selectedLogs, setSelectedLogs] = useState<string | null>(null);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [selectedExecution, setSelectedExecution] = useState<ExtendedExecution | null>(null);

  useEffect(() => {
    const loadData = async () => {
      try {
        setIsLoading(true);
        const scriptsResponse = await api.get<Script[]>('/api/scripts');
        setScripts(scriptsResponse.data);

        const allExecutions: ExtendedExecution[] = [];
        for (const script of scriptsResponse.data) {
          const executionsResponse = await api.get<Execution[]>(`/api/scripts/${script.id}/executions`);
          allExecutions.push(
            ...executionsResponse.data.map((execution: Execution) => ({
              ...execution,
              scriptName: script.name
            }))
          );
        }

        // Sort executions by date, most recent first
        allExecutions.sort((a, b) => new Date(b.started_at).getTime() - new Date(a.started_at).getTime());
        setExecutions(allExecutions);
      } catch (error) {
        console.error('Failed to load data:', error);
      } finally {
        setIsLoading(false);
      }
    };

    loadData();
  }, []);

  const handleScriptChange = (value: string | null) => {
    setSelectedScript(value);
    if (value) {
      setSearchParams({ script: value });
    } else {
      setSearchParams({});
    }
  };

  const filteredExecutions = selectedScript
    ? executions.filter(execution => execution.scriptName === selectedScript)
    : executions;

  const scriptOptions = scripts.map(script => ({
    value: script.name,
    label: script.name,
  }));

  const closeLogModal = () => {
    setIsModalOpen(false);
    setSelectedExecution(null);
    setSelectedLogs(null);
  };

  return (
    <div style={{ maxWidth: '1200px', margin: '0 auto', padding: '20px', position: 'relative', minHeight: '200px' }}>
      <LoadingOverlay visible={isLoading} />
      <Stack gap="md">
        <Title order={2}>Execution Logs</Title>
        
        <Select
          label="Filter by Script"
          placeholder="Select a script"
          data={scriptOptions}
          value={selectedScript}
          onChange={handleScriptChange}
          clearable
          style={{ maxWidth: '300px' }}
        />

        <div style={{ 
          display: 'grid', 
          gridTemplateColumns: 'repeat(auto-fill, minmax(350px, 1fr))', 
          gap: '1rem' 
        }}>
          {filteredExecutions.map((execution) => (
            <Card 
              key={execution.id} 
              shadow="sm" 
              padding="lg" 
              radius="md" 
              withBorder 
              style={{ cursor: 'pointer' }}
              onClick={() => {
                setSelectedLogs(execution.log_output || '');
                setSelectedExecution(execution);
                setIsModalOpen(true);
              }}
            >
              <Group justify="space-between" mb="xs">
                <Text fw={500}>{execution.scriptName}</Text>
                <Badge 
                  color={
                    execution.status === ExecutionStatus.SUCCESS ? 'green' : 
                    execution.status === ExecutionStatus.PENDING ? 'yellow' : 
                    execution.status === ExecutionStatus.RUNNING ? 'blue' : 'red'
                  }
                  leftSection={
                    execution.status === ExecutionStatus.SUCCESS ? (
                      <IconCheck size={12} />
                    ) : execution.status === ExecutionStatus.RUNNING ? (
                      <IconLoader2 size={12} className="rotating" />
                    ) : execution.status === ExecutionStatus.PENDING ? (
                      <IconClock size={12} />
                    ) : (
                      <IconX size={12} />
                    )
                  }
                >
                  {execution.status}
                </Badge>
              </Group>
              
              <Text size="sm" c="dimmed">
                {new Date(execution.started_at).toLocaleString()}
              </Text>
            </Card>
          ))}
          {!isLoading && filteredExecutions.length === 0 && (
            <Text c="dimmed" ta="center" style={{ gridColumn: '1 / -1', padding: '2rem' }}>
              No executions found
            </Text>
          )}
        </div>

        {isModalOpen && (
          <>
            <Box
              style={{
                position: 'fixed',
                top: 0,
                left: 0,
                right: 0,
                bottom: 0,
                backgroundColor: 'rgba(0, 0, 0, 0.85)',
                backdropFilter: 'blur(3px)',
                zIndex: 999
              }}
              onClick={closeLogModal}
            />
            <Box
              style={{
                position: 'fixed',
                top: '50%',
                left: '50%',
                transform: 'translate(-50%, -50%)',
                width: '800px',
                maxWidth: '90vw',
                maxHeight: '90vh',
                backgroundColor: '#1A1B1E',
                border: '1px solid #2C2E33',
                borderRadius: '8px',
                zIndex: 1000,
                display: 'flex',
                flexDirection: 'column'
              }}
            >
              <Box p="md" style={{ borderBottom: '1px solid #2C2E33', backgroundColor: '#141517' }}>
                <Group>
                  <Text size="lg" fw={500}>Execution Logs</Text>
                  {selectedExecution && (
                    <>
                      <Badge
                        color={
                          selectedExecution.status === ExecutionStatus.SUCCESS ? 'green' : 
                          selectedExecution.status === ExecutionStatus.PENDING ? 'yellow' : 
                          selectedExecution.status === ExecutionStatus.RUNNING ? 'blue' : 'red'
                        }
                        leftSection={
                          selectedExecution.status === ExecutionStatus.SUCCESS ? (
                            <IconCheck size={12} />
                          ) : selectedExecution.status === ExecutionStatus.RUNNING ? (
                            <IconLoader2 size={12} className="rotating" />
                          ) : selectedExecution.status === ExecutionStatus.PENDING ? (
                            <IconClock size={12} />
                          ) : (
                            <IconX size={12} />
                          )
                        }
                      >
                        {selectedExecution.status}
                      </Badge>
                      <Text size="sm" c="dimmed">
                        {new Date(selectedExecution.started_at).toLocaleString()}
                      </Text>
                    </>
                  )}
                </Group>
              </Box>

              <Box p="md" style={{ flex: 1, overflowY: 'auto', maxHeight: 'calc(90vh - 140px)' }}>
                {selectedExecution?.error_message && (
                  <Text c="red" size="sm" mb="md">
                    Error: {selectedExecution.error_message}
                  </Text>
                )}

                <Code block style={{ 
                  whiteSpace: 'pre-wrap', 
                  fontFamily: 'monospace',
                  padding: '1rem',
                  backgroundColor: '#141517',
                  border: '1px solid #2C2E33',
                  borderRadius: '4px'
                }}>
                  {selectedLogs || 'No logs available'}
                </Code>
              </Box>

              <Box p="md" style={{ borderTop: '1px solid #2C2E33', backgroundColor: '#141517' }}>
                <Group justify="flex-end">
                  <Button onClick={closeLogModal} variant="filled" color="gray">
                    Close
                  </Button>
                </Group>
              </Box>
            </Box>
          </>
        )}
      </Stack>
    </div>
  );
} 
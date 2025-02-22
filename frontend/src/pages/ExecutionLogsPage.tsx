import { useEffect, useState } from 'react';
import { Card, Select, Text, Group, Box, Stack, Title, Container, Combobox, InputBase, useCombobox, Portal, Paper, ActionIcon } from '@mantine/core';
import { useApi } from '../hooks/useApi';
import { Script, Execution } from '../types';
import { useSearchParams } from 'react-router-dom';
import { 
  IconCheck,
  IconX,
  IconClock,
  IconLoader2,
  IconFilter,
} from '@tabler/icons-react';
import { ExecutionStatus } from '../types';
import { formatDate, formatDuration } from '../utils/date';

interface ExtendedExecution extends Execution {
  scriptName: string;
}

export function ExecutionLogsPage() {
  const api = useApi();
  const [searchParams, setSearchParams] = useSearchParams();
  const [scripts, setScripts] = useState<Script[]>([]);
  const [executions, setExecutions] = useState<ExtendedExecution[]>([]);
  const [selectedExecution, setSelectedExecution] = useState<ExtendedExecution | null>(null);
  const [logContent, setLogContent] = useState<string>('');
  const [scriptSearch, setScriptSearch] = useState('');
  const [isLoading, setIsLoading] = useState(true);
  const [isLogModalOpen, setIsLogModalOpen] = useState(false);

  const selectedScript = searchParams.get('script') || '';
  const selectedStatus = searchParams.get('status') || '';

  const combobox = useCombobox({
    onDropdownClose: () => {
      combobox.resetSelectedOption();
      setScriptSearch(selectedScript); // Reset search to selected value
    },
  });

  const filteredScripts = scripts
    .filter(script => 
      script.name.toLowerCase().includes(scriptSearch.toLowerCase())
    )
    .map(script => ({
      value: script.name,
      label: script.name,
    }));

  const statusOptions = [
    { 
      value: '', 
      label: 'All Statuses',
      leftSection: <IconFilter size={16} style={{ opacity: 0.5 }} />
    },
    { 
      value: ExecutionStatus.SUCCESS, 
      label: 'Success',
      leftSection: <IconCheck size={16} color="var(--mantine-color-green-filled)" />
    },
    { 
      value: ExecutionStatus.RUNNING, 
      label: 'Running',
      leftSection: <IconLoader2 size={16} color="var(--mantine-color-blue-filled)" className="rotating" />
    },
    { 
      value: ExecutionStatus.PENDING, 
      label: 'Pending',
      leftSection: <IconClock size={16} color="var(--mantine-color-yellow-filled)" />
    },
    { 
      value: ExecutionStatus.FAILURE, 
      label: 'Failed',
      leftSection: <IconX size={16} color="var(--mantine-color-red-filled)" />
    }
  ];

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

        // Filter by script name if selected
        let filteredExecutions = allExecutions;
        if (selectedScript) {
          filteredExecutions = filteredExecutions.filter(execution => execution.scriptName === selectedScript);
        }

        // Filter by status if selected
        if (selectedStatus) {
          filteredExecutions = filteredExecutions.filter(execution => execution.status === selectedStatus);
        }

        setExecutions(filteredExecutions);
      } catch (error) {
        console.error('Failed to load data:', error);
      } finally {
        setIsLoading(false);
      }
    };

    loadData();
  }, [selectedScript, selectedStatus]);

  const handleScriptChange = (value: string | null) => {
    const newParams = new URLSearchParams(searchParams);
    if (value) {
      newParams.set('script', value);
    } else {
      newParams.delete('script');
    }
    setSearchParams(newParams);
    setScriptSearch(value || '');
  };

  const handleStatusChange = (value: string | null) => {
    const newParams = new URLSearchParams(searchParams);
    if (value) {
      newParams.set('status', value);
    } else {
      newParams.delete('status');
    }
    setSearchParams(newParams);
  };

  const openLogModal = (execution: ExtendedExecution) => {
    setSelectedExecution(execution);
    setLogContent(execution.log_output || '');
    setIsLogModalOpen(true);
  };

  return (
    <Box p="xl">
      <Container size="xl">
        <Stack gap="lg">
          <Title>Execution Logs</Title>

          <Group align="flex-start">
            <Box style={{ flex: 1, maxWidth: 300 }}>
              <Combobox
                store={combobox}
                onOptionSubmit={(value) => {
                  handleScriptChange(value);
                  combobox.closeDropdown();
                }}
              >
                <Combobox.Target>
                  <InputBase
                    label="Filter by Script"
                    placeholder="Search or select script"
                    value={scriptSearch}
                    onChange={(event) => {
                      setScriptSearch(event.currentTarget.value);
                      combobox.openDropdown();
                    }}
                    onClick={() => combobox.openDropdown()}
                    rightSection={<Combobox.Chevron />}
                    rightSectionPointerEvents="none"
                  />
                </Combobox.Target>

                <Combobox.Dropdown>
                  <Combobox.Options>
                    <Combobox.Option value="">All Scripts</Combobox.Option>
                    {filteredScripts.map((script) => (
                      <Combobox.Option key={script.value} value={script.value}>
                        {script.label}
                      </Combobox.Option>
                    ))}
                  </Combobox.Options>
                </Combobox.Dropdown>
              </Combobox>
            </Box>

            <Box style={{ flex: 1, maxWidth: 300 }}>
              <Select
                label="Filter by Status"
                placeholder="All Statuses"
                data={statusOptions}
                value={selectedStatus}
                onChange={handleStatusChange}
              />
            </Box>
          </Group>

          <div style={{ 
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fill, minmax(250px, 1fr))',
            gap: '1rem',
            width: '100%'
          }}>
            {executions.map((execution) => (
              <Card
                key={execution.id}
                withBorder
                padding="md"
                onClick={() => openLogModal(execution)}
                style={{
                  cursor: 'pointer',
                  backgroundColor: 
                    execution.status === ExecutionStatus.SUCCESS ? 'rgba(34, 197, 94, 0.05)' :
                    execution.status === ExecutionStatus.RUNNING ? 'rgba(59, 130, 246, 0.05)' :
                    execution.status === ExecutionStatus.PENDING ? 'rgba(234, 179, 8, 0.05)' :
                    'rgba(239, 68, 68, 0.05)',
                  borderColor: 
                    execution.status === ExecutionStatus.SUCCESS ? 'rgba(34, 197, 94, 0.2)' :
                    execution.status === ExecutionStatus.RUNNING ? 'rgba(59, 130, 246, 0.2)' :
                    execution.status === ExecutionStatus.PENDING ? 'rgba(234, 179, 8, 0.2)' :
                    'rgba(239, 68, 68, 0.2)',
                  transition: 'all 0.2s ease',
                  '&:hover': {
                    transform: 'translateY(-4px)',
                    backgroundColor: 
                      execution.status === ExecutionStatus.SUCCESS ? 'rgba(34, 197, 94, 0.1)' :
                      execution.status === ExecutionStatus.RUNNING ? 'rgba(59, 130, 246, 0.1)' :
                      execution.status === ExecutionStatus.PENDING ? 'rgba(234, 179, 8, 0.1)' :
                      'rgba(239, 68, 68, 0.1)',
                  }
                }}
              >
                <Stack gap="sm">
                  <Group gap="xs">
                    {execution.status === ExecutionStatus.SUCCESS ? (
                      <IconCheck 
                        size={18} 
                        style={{ 
                          color: 'var(--mantine-color-green-filled)',
                          filter: 'drop-shadow(0 0 8px rgba(34, 197, 94, 0.4))'
                        }} 
                      />
                    ) : execution.status === ExecutionStatus.RUNNING ? (
                      <IconLoader2 
                        size={18} 
                        className="rotating" 
                        style={{ 
                          color: 'var(--mantine-color-blue-filled)',
                          filter: 'drop-shadow(0 0 8px rgba(59, 130, 246, 0.4))'
                        }} 
                      />
                    ) : execution.status === ExecutionStatus.PENDING ? (
                      <IconClock 
                        size={18} 
                        style={{ 
                          color: 'var(--mantine-color-yellow-filled)',
                          filter: 'drop-shadow(0 0 8px rgba(234, 179, 8, 0.4))'
                        }} 
                      />
                    ) : (
                      <IconX 
                        size={18} 
                        style={{ 
                          color: 'var(--mantine-color-red-filled)',
                          filter: 'drop-shadow(0 0 8px rgba(239, 68, 68, 0.4))'
                        }} 
                      />
                    )}
                    <Text fw={500} size="sm" style={{ color: '#C1C2C5' }}>
                      {execution.status}
                    </Text>
                  </Group>

                  <Stack gap={4}>
                    <Text size="sm" c="dimmed" style={{ fontSize: '0.9rem' }}>
                      Script: {execution.scriptName}
                    </Text>
                    <Text size="sm" c="dimmed" style={{ fontSize: '0.9rem' }}>
                      Started: {formatDate(execution.started_at)}
                    </Text>
                    {execution.completed_at && (
                      <Text size="sm" c="dimmed" style={{ fontSize: '0.9rem' }}>
                        Duration: {formatDuration(execution.started_at, execution.completed_at)}
                      </Text>
                    )}
                  </Stack>
                </Stack>
              </Card>
            ))}
            {!isLoading && executions.length === 0 && (
              <Text c="dimmed" ta="center">No executions found</Text>
            )}
          </div>
        </Stack>
      </Container>

      {/* Log Modal */}
      {isLogModalOpen && (
        <Portal>
          <div
            style={{
              position: 'fixed',
              top: 0,
              left: 0,
              right: 0,
              bottom: 0,
              backgroundColor: 'rgba(0, 0, 0, 0.75)',
              zIndex: 1000,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
            }}
          >
            <Paper
              style={{
                width: '90%',
                maxWidth: '1000px',
                maxHeight: '90vh',
                margin: '20px',
                position: 'relative',
              }}
              p="md"
            >
              <Stack>
                <Group justify="space-between" mb="md">
                  <Stack gap={0}>
                    <Title order={3}>Execution Log</Title>
                    <Group gap="xs">
                      <Text size="sm" c="dimmed">
                        {formatDate(selectedExecution?.started_at || '')}
                      </Text>
                      {selectedExecution && (
                        <Text size="sm" c="dimmed">
                          • Duration: {formatDuration(selectedExecution.started_at, selectedExecution.completed_at)}
                        </Text>
                      )}
                    </Group>
                  </Stack>
                  <ActionIcon 
                    onClick={() => setIsLogModalOpen(false)}
                    variant="subtle"
                  >
                    ✕
                  </ActionIcon>
                </Group>

                <Paper
                  withBorder
                  p="md"
                  style={{
                    height: '500px',
                    overflowY: 'auto',
                    backgroundColor: '#1A1B1E',
                    fontFamily: 'monospace',
                    fontSize: '13px',
                  }}
                >
                  {logContent ? (
                    logContent.split('\n').map((line, index) => (
                      <div
                        key={index}
                        style={{
                          display: 'block',
                          whiteSpace: 'pre-line',
                          color: '#d4d4d4',
                          padding: '2px 8px',
                          lineHeight: '1.5',
                          overflowWrap: 'break-word'
                        }}
                      >
                        {line.replace(/^ERROR: /, '')}
                      </div>
                    ))
                  ) : (
                    <Text c="dimmed" ta="center">
                      No logs available
                    </Text>
                  )}
                </Paper>
              </Stack>
            </Paper>
          </div>
        </Portal>
      )}
    </Box>
  );
} 
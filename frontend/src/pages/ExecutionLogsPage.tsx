import { useEffect, useState } from 'react';
import { Card, Select, Text, Group, Badge, Box, Stack, Title, Container, Combobox, InputBase, useCombobox, Portal, Paper, ActionIcon } from '@mantine/core';
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
import { formatDate } from '../utils/date';

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

  const openLogModal = (content: string) => {
    setLogContent(content);
    setIsLogModalOpen(true);
  };

  const closeLogModal = () => {
    setLogContent('');
    setIsLogModalOpen(false);
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
            gridTemplateColumns: 'repeat(auto-fill, minmax(350px, 1fr))', 
            gap: '1rem' 
          }}>
            {executions.map((execution) => (
              <Card 
                key={execution.id} 
                shadow="sm" 
                padding="lg" 
                radius="md" 
                withBorder 
                style={{ cursor: 'pointer' }}
                onClick={() => {
                  openLogModal(execution.log_output || '');
                  setSelectedExecution(execution);
                }}
              >
                <Group justify="space-between" mb="xs">
                  <Text fw={500}>{execution.scriptName}</Text>
                  {execution.status === ExecutionStatus.SUCCESS ? (
                    <IconCheck size={18} color="var(--mantine-color-green-filled)" />
                  ) : execution.status === ExecutionStatus.RUNNING ? (
                    <IconLoader2 size={18} className="rotating" color="var(--mantine-color-blue-filled)" />
                  ) : execution.status === ExecutionStatus.PENDING ? (
                    <IconClock size={18} color="var(--mantine-color-yellow-filled)" />
                  ) : (
                    <IconX size={18} color="var(--mantine-color-red-filled)" />
                  )}
                  <Badge
                    color={
                      execution.status === ExecutionStatus.SUCCESS ? 'green' : 
                      execution.status === ExecutionStatus.PENDING ? 'yellow' : 
                      execution.status === ExecutionStatus.RUNNING ? 'blue' : 'red'
                    }
                  >
                    {execution.status.toUpperCase()}
                  </Badge>
                </Group>
                
                <Text size="sm" c="dimmed">
                  {formatDate(execution.started_at)}
                </Text>
              </Card>
            ))}
            {!isLoading && executions.length === 0 && (
              <Text c="dimmed" ta="center" style={{ gridColumn: '1 / -1', padding: '2rem' }}>
                No executions found
              </Text>
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
                  <Title order={3}>
                    Execution Log
                    {selectedExecution?.started_at && (
                      <Text size="sm" c="dimmed" mt={4}>
                        {formatDate(selectedExecution.started_at)}
                      </Text>
                    )}
                  </Title>
                  <ActionIcon 
                    onClick={closeLogModal}
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
                      <Text
                        key={index}
                        style={{
                          whiteSpace: 'pre-wrap',
                          color: '#d4d4d4',
                          padding: '2px 0',
                          fontSize: 'inherit',
                        }}
                      >
                        {line.replace(/^ERROR: /, '')}
                      </Text>
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
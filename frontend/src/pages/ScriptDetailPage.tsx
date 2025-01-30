import { useState, useEffect } from 'react';
import {
  Box,
  TextInput,
  Group,
  Button,
  Stack,
  Text,
  LoadingOverlay,
  Code,
  Card,
  Badge,
  Switch,
  Table,
  Modal,
} from '@mantine/core';
import { useParams, useNavigate } from 'react-router-dom';
import { notifications } from '@mantine/notifications';
import { 
  IconPlayerPlay, 
  IconLoader2,
  IconTrash,
  IconCheck,
  IconX,
  IconClock,
} from '@tabler/icons-react';
import { CodeEditor } from '../components/CodeEditor';
import { TagInput } from '../components/TagInput';
import { DependencyInput } from '../components/DependencyInput';
import { ScheduleInput } from '../components/ScheduleInput';
import { useScript } from '../hooks/useScript';
import { scriptsApi } from '../api/client';
import { Tag, Dependency, Schedule, Execution } from '../types';
import { WS_BASE_URL } from '../config';
import axios from 'axios';

export function ScriptDetailPage() {
  const { id } = useParams();
  const scriptId = Number(id);
  const { script, isLoading, error, mutate } = useScript(scriptId);
  const [isSaving, setIsSaving] = useState(false);
  const [isRunning, setIsRunning] = useState(false);
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [content, setContent] = useState('');
  const [tags, setTags] = useState<Tag[]>([]);
  const [dependencies, setDependencies] = useState<Dependency[]>([]);
  const [schedules, setSchedules] = useState<Schedule[]>([]);
  const [executions, setExecutions] = useState<Execution[]>([]);
  const [lastError, setLastError] = useState<string | null>(null);
  const [isExecutionModalOpen, setIsExecutionModalOpen] = useState(false);
  const [executionOutput, setExecutionOutput] = useState<string[]>([]);
  const [ws, setWs] = useState<WebSocket | null>(null);
  const [selectedExecution, setSelectedExecution] = useState<Execution | null>(null);
  const [isLogModalOpen, setIsLogModalOpen] = useState(false);
  const [logContent, setLogContent] = useState<string>('');
  const [isInstallingDeps, setIsInstallingDeps] = useState(false);
  const [isActive, setIsActive] = useState(true);
  const [isDeleteModalOpen, setIsDeleteModalOpen] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);
  const navigate = useNavigate();

  useEffect(() => {
    if (script) {
      try {
        console.log('Received script data:', script);
        setName(script.name);
        setDescription(script.description || '');
        setContent(script.content);
        setTags(Array.isArray(script.tags) ? script.tags : []);
        setDependencies(Array.isArray(script.dependencies) ? script.dependencies : []);
        setSchedules(Array.isArray(script.schedules) ? script.schedules : []);
        setIsActive(script.is_active);
        setLastError(null);
      } catch (err) {
        console.error('Error processing script data:', err);
        const error = err as Error;
        setLastError(`Error processing script data: ${error.message}`);
      }
    }
  }, [script]);

  const handleApiError = (err: unknown, action: string) => {
    console.error(`Error during ${action}:`, err);
    let errorMessage = 'An unknown error occurred';
    
    if (err instanceof Error) {
      errorMessage = err.message;
    }
    
    if (axios.isAxiosError(err)) {
      console.log('Axios error response:', err.response);
      if (err.response?.data) {
        try {
          // Try to parse the error response if it's JSON
          const data = typeof err.response.data === 'string' 
            ? JSON.parse(err.response.data) 
            : err.response.data;
          errorMessage = data.detail || JSON.stringify(data);
        } catch (parseErr) {
          // If parsing fails, use the raw response data
          errorMessage = err.response.data.toString();
        }
      }
    }
    
    setLastError(errorMessage);
    notifications.show({
      title: 'Error',
      message: errorMessage,
      color: 'red',
    });
  };

  const handleSave = async () => {
    setIsSaving(true);
    try {
      await scriptsApi.update(scriptId, { content });
      await mutate();
      setLastError(null);
      notifications.show({
        title: 'Success',
        message: 'Script saved successfully',
        color: 'green',
      });
    } catch (err) {
      handleApiError(err, 'saving script');
    } finally {
      setIsSaving(false);
    }
  };

  const handleNameChange = async (newName: string) => {
    setName(newName);
    try {
      await scriptsApi.update(scriptId, { name: newName });
      await mutate();
      setLastError(null);
    } catch (err) {
      handleApiError(err, 'updating name');
    }
  };

  const handleDescriptionChange = async (newDescription: string) => {
    setDescription(newDescription);
    try {
      await scriptsApi.update(scriptId, { description: newDescription });
      await mutate();
      setLastError(null);
    } catch (err) {
      handleApiError(err, 'updating description');
    }
  };

  const handleTagsChange = async (newTags: Tag[]) => {
    try {
      setTags(newTags);
      await scriptsApi.update(scriptId, {
        tags: newTags.map(t => t.name),
      });
      await mutate();
      setLastError(null);
    } catch (err) {
      handleApiError(err, 'updating tags');
    }
  };

  const handleDependenciesChange = async (newDependencies: Dependency[]) => {
    // Find removed dependencies
    const removedDependencies = dependencies.filter(
      oldDep => !newDependencies.some(newDep => newDep.package_name === oldDep.package_name)
    );

    // If we have removed dependencies, uninstall them
    if (removedDependencies.length > 0) {
      try {
        setIsInstallingDeps(true);
        await Promise.all(
          removedDependencies.map(dep => 
            scriptsApi.uninstallDependency(scriptId, dep.package_name)
          )
        );
        notifications.show({
          title: 'Success',
          message: 'Dependencies uninstalled successfully',
          color: 'green',
        });
      } catch (err) {
        handleApiError(err, 'uninstalling dependencies');
        return; // Don't update the state if uninstall failed
      } finally {
        setIsInstallingDeps(false);
      }
    }

    // Update the script with new dependencies
    try {
      const updatedScript = await scriptsApi.update(scriptId, {
        dependencies: newDependencies.map(dep => ({
          package_name: dep.package_name,
          version_spec: dep.version_spec,
        })),
      });
      await mutate(updatedScript);
      setLastError(null);
    } catch (err) {
      handleApiError(err, 'updating dependencies');
    }
  };

  const handleDeleteDependency = async (packageName: string) => {
    try {
      setIsInstallingDeps(true);
      await scriptsApi.uninstallDependency(scriptId, packageName);
      const updatedDependencies = dependencies.filter(dep => dep.package_name !== packageName);
      await handleDependenciesChange(updatedDependencies);
      notifications.show({
        title: 'Success',
        message: `${packageName} uninstalled successfully`,
        color: 'green',
      });
    } catch (err) {
      handleApiError(err, 'uninstalling dependency');
    } finally {
      setIsInstallingDeps(false);
    }
  };

  const handleSchedulesChange = async (newSchedules: Schedule[]) => {
    try {
      setSchedules(newSchedules);
      await scriptsApi.update(scriptId, {
        schedules: newSchedules.map(s => ({
          cron_expression: s.cron_expression,
          description: s.description,
        })),
      });
      await mutate();
      setLastError(null);
    } catch (err) {
      handleApiError(err, 'updating schedules');
    }
  };

  const handleContentChange = (newContent: string) => {
    setContent(newContent);
  };

  const loadExecutions = async () => {
    try {
      const data = await scriptsApi.listExecutions(scriptId);
      console.log('Loaded executions:', data);
      setExecutions(data);
    } catch (err) {
      handleApiError(err, 'loading executions');
    }
  };

  useEffect(() => {
    if (scriptId) {
      loadExecutions();
    }
  }, [scriptId]);

  const handleRun = async () => {
    setIsRunning(true);
    setExecutionOutput([]);
    setIsExecutionModalOpen(true);

    try {
      // Create WebSocket connection using the config
      const wsUrl = `${WS_BASE_URL}/api/scripts/${scriptId}/ws`;
      console.log('Connecting to WebSocket:', wsUrl);
      const socket = new WebSocket(wsUrl);
      setWs(socket);

      socket.onopen = () => {
        console.log('WebSocket connected');
      };

      socket.onmessage = (event) => {
        console.log('Received WebSocket message:', event.data);
        setExecutionOutput(prev => {
          console.log('Current output:', prev);
          console.log('Adding line:', event.data);
          return [...prev, event.data];
        });
      };

      socket.onerror = (error) => {
        console.error('WebSocket error:', error);
        handleApiError(error, 'WebSocket connection');
        setIsRunning(false);
      };

      socket.onclose = async () => {
        console.log('WebSocket closed');
        setIsRunning(false);
        // Wait a short delay to ensure the backend has saved the execution
        await new Promise(resolve => setTimeout(resolve, 1000));
        await loadExecutions(); // Refresh execution history
      };

    } catch (err) {
      handleApiError(err, 'executing script');
      setIsRunning(false);
    }
  };

  const closeExecutionModal = () => {
    if (ws) {
      ws.close();
    }
    setIsExecutionModalOpen(false);
    setExecutionOutput([]);
    setWs(null);
  };

  const handleViewLogs = async (execution: Execution) => {
    try {
      console.log('handleViewLogs called for execution:', execution);
      setLogContent('Loading logs...');
      setSelectedExecution(execution);
      setIsLogModalOpen(true);
      console.log('Modal state set to open, isLogModalOpen:', true);

      console.log('Fetching logs for execution:', execution.id);
      const logs = await scriptsApi.getExecutionLogs(scriptId, execution.id);
      console.log('Received logs:', logs);
      
      if (!logs && logs !== '') {
        console.log('No logs available');
        setLogContent('No logs available');
      } else {
        console.log('Setting log content, length:', logs.length);
        setLogContent(logs);
      }
    } catch (err) {
      console.error('Error in handleViewLogs:', err);
      handleApiError(err, 'loading logs');
      setLogContent('Error loading logs');
    }
  };

  const closeLogModal = () => {
    console.log('closeLogModal called');
    setIsLogModalOpen(false);
    setSelectedExecution(null);
    setLogContent('');
  };

  // Add effect to monitor modal state
  useEffect(() => {
    console.log('Modal state changed - isLogModalOpen:', isLogModalOpen);
  }, [isLogModalOpen]);

  const handleInstallDependencies = async () => {
    setIsInstallingDeps(true);
    try {
      await scriptsApi.installDependencies(scriptId);
      // Refresh script data to get updated dependency versions
      await mutate();
      setLastError(null);
      notifications.show({
        title: 'Success',
        message: 'Dependencies installed successfully',
        color: 'green',
      });
    } catch (err) {
      handleApiError(err, 'installing dependencies');
    } finally {
      setIsInstallingDeps(false);
    }
  };

  const handleToggleActive = async () => {
    try {
      // Check if we can enable the script
      if (!isActive) {
        // Can't enable if no schedules
        if (!script?.schedules.length) {
          notifications.show({
            title: 'Error',
            message: 'Cannot enable script without any schedules',
            color: 'red',
          });
          return;
        }
        
        // Can't enable if dependencies not installed
        const hasUninstalledDeps = script?.dependencies.some(
          (dep: Dependency) => !dep.installed_version
        );
        if (hasUninstalledDeps) {
          notifications.show({
            title: 'Error',
            message: 'Cannot enable script with uninstalled dependencies',
            color: 'red',
          });
          return;
        }
      }

      const newIsActive = !isActive;
      setIsActive(newIsActive);
      await scriptsApi.update(scriptId, { is_active: newIsActive });
      await mutate();
      notifications.show({
        title: 'Success',
        message: `Scheduled executions ${newIsActive ? 'enabled' : 'disabled'}`,
        color: 'green',
      });
    } catch (err) {
      handleApiError(err, 'toggling script status');
      setIsActive(!isActive); // Revert on error
    }
  };

  // Helper function to check if toggle should be disabled
  const isToggleDisabled = () => {
    if (!script) return true;
    if (isActive) return false; // Can always disable
    return (
      !script.schedules.length || // No schedules
      script.dependencies.some(dep => !dep.installed_version) // Uninstalled deps
    );
  };

  const handleDelete = async () => {
    setIsDeleting(true);
    try {
      await scriptsApi.delete(scriptId);
      notifications.show({
        title: 'Success',
        message: 'Script deleted successfully',
        color: 'green',
      });
      navigate('/scripts');
    } catch (err) {
      handleApiError(err, 'deleting script');
    } finally {
      setIsDeleting(false);
      setIsDeleteModalOpen(false);
    }
  };

  if (isLoading) return <LoadingOverlay visible />;
  if (error) return <Text c="red">Error loading script: {error.message}</Text>;

  return (
    <Box p="xl" pos="relative">
      {isExecutionModalOpen && (
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
            onClick={closeExecutionModal}
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
                <Text size="lg" fw={500}>Script Execution</Text>
                {isRunning && (
                  <Badge
                    color="blue"
                    variant="filled"
                    size="sm"
                    leftSection={
                      <IconLoader2 
                        size={14}
                        className="rotating"
                        style={{ marginRight: '4px' }}
                      />
                    }
                  >
                    Running
                  </Badge>
                )}
              </Group>
            </Box>

            <Box p="md" style={{ flex: 1, overflowY: 'auto', maxHeight: 'calc(90vh - 140px)' }}>
              <Code block style={{ 
                whiteSpace: 'pre-wrap', 
                fontFamily: 'monospace',
                padding: '1rem',
                backgroundColor: '#141517',
                border: '1px solid #2C2E33',
                borderRadius: '4px',
                minHeight: '300px'
              }}>
                {executionOutput.join('')}
              </Code>
            </Box>

            <Box p="md" style={{ borderTop: '1px solid #2C2E33', backgroundColor: '#141517' }}>
              <Group justify="flex-end">
                <Button 
                  onClick={closeExecutionModal}
                  variant="filled"
                  color="gray"
                  disabled={isRunning}
                >
                  Close
                </Button>
              </Group>
            </Box>
          </Box>
        </>
      )}

      {isLogModalOpen && (
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
                        selectedExecution.status === 'SUCCESS' ? 'green' : 
                        selectedExecution.status === 'PENDING' ? 'yellow' : 
                        selectedExecution.status === 'RUNNING' ? 'blue' : 'red'
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
                {logContent || 'No logs available'}
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

      <Stack gap="xl">
        <Group justify="space-between" align="flex-start" w="100%">
          <Box style={{ flex: 1, paddingRight: '24px' }}>
            <Box style={{ width: '100%', maxWidth: '600px', marginLeft: 0 }}>
              <TextInput
                size="xl"
                placeholder="Script Name"
                value={name}
                onChange={(e) => handleNameChange(e.target.value)}
                styles={{
                  root: {
                    width: '100%'
                  },
                  input: {
                    fontSize: '24px',
                    fontWeight: 700,
                    backgroundColor: 'transparent',
                    border: 'none',
                    textAlign: 'left',
                    padding: 0,
                    transition: 'all 0.2s ease',
                    '&:not(:focus)': {
                      backgroundColor: 'transparent',
                      border: 'none',
                    },
                    '&:focus': {
                      backgroundColor: 'rgba(0,0,0,0.2)',
                      border: '1px solid #2C2E33',
                      padding: '8px 12px',
                    },
                    '&::placeholder': {
                      color: '#666'
                    }
                  },
                  wrapper: {
                    backgroundColor: 'transparent'
                  }
                }}
              />
              <TextInput
                placeholder="Description"
                value={description}
                onChange={(e) => handleDescriptionChange(e.target.value)}
                styles={{
                  root: {
                    width: '100%'
                  },
                  input: {
                    backgroundColor: 'transparent',
                    border: 'none',
                    textAlign: 'left',
                    padding: 0,
                    transition: 'all 0.2s ease',
                    '&:not(:focus)': {
                      backgroundColor: 'transparent',
                      border: 'none',
                    },
                    '&:focus': {
                      backgroundColor: 'rgba(0,0,0,0.2)',
                      border: '1px solid #2C2E33',
                      padding: '8px 12px',
                    },
                    '&::placeholder': {
                      color: '#666'
                    }
                  },
                  wrapper: {
                    backgroundColor: 'transparent'
                  }
                }}
              />
            </Box>
          </Box>
          <Group>
            <Group gap="xs">
              <Switch
                checked={isActive}
                onChange={handleToggleActive}
                disabled={isToggleDisabled()}
                label={isActive ? 'Active' : 'Inactive'}
              />
            </Group>
            <Button
              leftSection={<IconPlayerPlay size={18} />}
              onClick={handleRun}
              loading={isRunning}
              color="green"
            >
              Run Script
            </Button>
            <Button
              onClick={handleSave}
              loading={isSaving}
            >
              Save Changes
            </Button>
            <Button
              variant="light"
              color="red"
              onClick={() => setIsDeleteModalOpen(true)}
              leftSection={<IconTrash size={18} />}
            >
              Delete Script
            </Button>
          </Group>
        </Group>
        
        {lastError && (
          <Text c="red" mb="md">
            Error: {lastError}
            <Code block>{JSON.stringify(script, null, 2)}</Code>
          </Text>
        )}
        
        <div style={{ 
          display: 'grid',
          gridTemplateColumns: '70% 30%',
          gap: '24px',
          width: '100%'
        }}>
          {/* Left Column */}
          <Stack gap="xl">
            <Card withBorder>
              <Text fw={500} size="lg" mb="md">Dependencies</Text>
              <Stack>
                <DependencyInput
                  value={dependencies}
                  onChange={handleDependenciesChange}
                />
                
                <Box style={{ overflowX: 'auto', backgroundColor: '#1A1B1E', border: '1px solid #2C2E33', borderRadius: '4px' }}>
                  <Table
                    withTableBorder
                    highlightOnHover
                    style={{ 
                      minWidth: '600px', 
                      width: '100%',
                      backgroundColor: '#1A1B1E'
                    }}
                  >
                    <colgroup>
                      <col style={{ width: '35%' }} />
                      <col style={{ width: '25%' }} />
                      <col style={{ width: '30%' }} />
                      <col style={{ width: '10%' }} />
                    </colgroup>
                    <thead>
                      <tr style={{ backgroundColor: '#141517' }}>
                        <th style={{ 
                          padding: '12px 16px',
                          color: '#C1C2C5',
                          fontWeight: 600,
                          fontSize: '0.9rem',
                          textAlign: 'left',
                          borderBottom: '1px solid #2C2E33',
                          backgroundColor: '#141517'
                        }}>Package</th>
                        <th style={{ 
                          padding: '12px 16px',
                          color: '#C1C2C5',
                          fontWeight: 600,
                          fontSize: '0.9rem',
                          textAlign: 'left',
                          borderBottom: '1px solid #2C2E33',
                          backgroundColor: '#141517'
                        }}>Version</th>
                        <th style={{ 
                          padding: '12px 16px',
                          color: '#C1C2C5',
                          fontWeight: 600,
                          fontSize: '0.9rem',
                          textAlign: 'left',
                          borderBottom: '1px solid #2C2E33',
                          backgroundColor: '#141517'
                        }}>Status</th>
                        <th style={{ 
                          padding: '12px 16px',
                          color: '#C1C2C5',
                          fontWeight: 600,
                          fontSize: '0.9rem',
                          textAlign: 'center',
                          borderBottom: '1px solid #2C2E33',
                          backgroundColor: '#141517'
                        }}>Actions</th>
                      </tr>
                    </thead>
                    <tbody>
                      {dependencies.map((dep: Dependency) => (
                        <tr key={`${dep.package_name}-${dep.version_spec}`} style={{ backgroundColor: '#1A1B1E' }}>
                          <td style={{ 
                            padding: '12px 16px',
                            color: '#C1C2C5',
                            borderBottom: '1px solid #2C2E33',
                            overflow: 'hidden',
                            textOverflow: 'ellipsis',
                            whiteSpace: 'nowrap'
                          }}>
                            {dep.package_name}
                          </td>
                          <td style={{ 
                            padding: '12px 16px',
                            color: '#C1C2C5',
                            borderBottom: '1px solid #2C2E33',
                            overflow: 'hidden',
                            textOverflow: 'ellipsis',
                            whiteSpace: 'nowrap'
                          }}>
                            {dep.version_spec || 'latest'}
                          </td>
                          <td style={{ 
                            padding: '12px 16px',
                            borderBottom: '1px solid #2C2E33',
                            textAlign: 'left'
                          }}>
                            <Badge
                              color={dep.installed_version ? 'green' : 'yellow'}
                              variant="filled"
                              size="sm"
                              style={{ 
                                minWidth: '100px', 
                                textAlign: 'center',
                                display: 'inline-block'
                              }}
                            >
                              {dep.installed_version ? `Installed (${dep.installed_version})` : 'Not Installed'}
                            </Badge>
                          </td>
                          <td style={{ 
                            padding: '12px 16px',
                            borderBottom: '1px solid #2C2E33',
                            textAlign: 'center'
                          }}>
                            <Button
                              variant="subtle"
                              color="red"
                              size="sm"
                              p={0}
                              onClick={() => handleDeleteDependency(dep.package_name)}
                              style={{ minWidth: 'unset' }}
                            >
                              <IconTrash size={18} />
                            </Button>
                          </td>
                        </tr>
                      ))}
                      {dependencies.length === 0 && (
                        <tr style={{ backgroundColor: '#1A1B1E' }}>
                          <td 
                            colSpan={4} 
                            style={{ 
                              padding: '12px 16px',
                              color: '#666',
                              textAlign: 'center',
                              borderBottom: '1px solid #2C2E33'
                            }}
                          >
                            No dependencies defined
                          </td>
                        </tr>
                      )}
                    </tbody>
                  </Table>
                </Box>
                
                <Group justify="flex-end">
                  <Button
                    onClick={handleInstallDependencies}
                    loading={isInstallingDeps}
                    disabled={dependencies.length === 0}
                  >
                    Install Dependencies
                  </Button>
                </Group>
              </Stack>
            </Card>

            <Card withBorder>
              <Text fw={500} size="lg" mb="md">Content</Text>
              <CodeEditor
                value={content}
                onChange={handleContentChange}
                height="600px"
              />
            </Card>
          </Stack>

          {/* Right Column */}
          <Stack gap="xl">
            <Card withBorder>
              <Text fw={500} size="lg" mb="md">Tags</Text>
              <TagInput
                value={tags}
                onChange={handleTagsChange}
              />
            </Card>

            <Card withBorder>
              <Text fw={500} size="lg" mb="md">Schedules</Text>
              <ScheduleInput
                value={schedules}
                onChange={handleSchedulesChange}
              />
            </Card>

            <Card withBorder>
              <Group justify="space-between" mb="md">
                <Text fw={500} size="lg">Execution History</Text>
                <Button
                  variant="light"
                  onClick={() => navigate(`/executions?script=${encodeURIComponent(name)}`)}
                >
                  View All Executions
                </Button>
              </Group>
              <div style={{ 
                display: 'grid',
                gridTemplateColumns: 'repeat(2, 1fr)',
                gap: '12px'
              }}>
                {executions.slice(0, 8).map((execution) => (
                  <Card 
                    key={execution.id}
                    withBorder
                    padding="sm"
                    style={{
                      backgroundColor: '#141517',
                      border: '1px solid #2C2E33'
                    }}
                  >
                    <Group justify="space-between" mb={4}>
                      <Group gap="xs">
                        {execution.status === 'SUCCESS' ? (
                          <IconCheck size={18} color="var(--mantine-color-green-filled)" />
                        ) : execution.status === 'RUNNING' ? (
                          <IconLoader2 size={18} className="rotating" color="var(--mantine-color-blue-filled)" />
                        ) : execution.status === 'PENDING' ? (
                          <IconClock size={18} color="var(--mantine-color-yellow-filled)" />
                        ) : (
                          <IconX size={18} color="var(--mantine-color-red-filled)" />
                        )}
                        <Text size="sm" c="dimmed" style={{ whiteSpace: 'nowrap' }}>
                          {new Date(execution.started_at).toLocaleString()}
                        </Text>
                      </Group>
                      <Button 
                        variant="subtle" 
                        size="xs"
                        onClick={() => handleViewLogs(execution)}
                        style={{ minWidth: 'unset', padding: '0 8px' }}
                      >
                        View Logs
                      </Button>
                    </Group>
                    {execution.error_message && (
                      <Text size="sm" c="red" mt={4} lineClamp={1}>
                        Error: {execution.error_message}
                      </Text>
                    )}
                  </Card>
                ))}
                {executions.length === 0 && (
                  <Text c="dimmed" ta="center" style={{ gridColumn: '1 / -1', padding: '2rem' }}>
                    No executions yet
                  </Text>
                )}
              </div>
            </Card>
          </Stack>
        </div>
      </Stack>

      <Modal 
        opened={isDeleteModalOpen} 
        onClose={() => setIsDeleteModalOpen(false)}
        title="Delete Script"
        centered
      >
        <Stack>
          <Text>Are you sure you want to delete this script? This action cannot be undone.</Text>
          <Group justify="flex-end">
            <Button variant="light" onClick={() => setIsDeleteModalOpen(false)}>
              Cancel
            </Button>
            <Button 
              color="red" 
              onClick={handleDelete}
              loading={isDeleting}
            >
              Delete
            </Button>
          </Group>
        </Stack>
      </Modal>

      <style>
        {`
          @keyframes rotate {
            from {
              transform: rotate(0deg);
            }
            to {
              transform: rotate(360deg);
            }
          }
          .rotating {
            animation: rotate 1s linear infinite;
          }
        `}
      </style>
    </Box>
  );
} 
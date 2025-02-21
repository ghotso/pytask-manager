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
  Paper,
  Portal,
  ActionIcon,
  Title,
  ScrollArea,
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
import { Tag, Dependency, Schedule, Execution, ExecutionStatus } from '../types';
import { WS_BASE_URL } from '../config';
import axios from 'axios';
import { formatDate } from '../utils/date';

export function ScriptDetailPage() {
  const { id } = useParams();
  const navigate = useNavigate();
  const scriptId = id ? parseInt(id) : 0;
  
  // Script data states
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [content, setContent] = useState('');
  const [tags, setTags] = useState<Tag[]>([]);
  const [dependencies, setDependencies] = useState<Dependency[]>([]);
  const [schedules, setSchedules] = useState<Schedule[]>([]);
  const [executions, setExecutions] = useState<Execution[]>([]);
  const [lastError, setLastError] = useState<string | null>(null);
  
  // Loading states
  const [isDeleting, setIsDeleting] = useState(false);
  const [isExecuting, setIsExecuting] = useState(false);
  
  // Modal states
  const [showExecutionModal, setShowExecutionModal] = useState(false);
  const [isLogModalOpen, setIsLogModalOpen] = useState(false);
  const [isDeleteModalOpen, setIsDeleteModalOpen] = useState(false);
  
  // Modal content states
  const [executionOutput, setExecutionOutput] = useState<string>('');
  const [executionStatus, setExecutionStatus] = useState<ExecutionStatus>(ExecutionStatus.PENDING);
  const [logContent, setLogContent] = useState('');
  const [selectedExecution, setSelectedExecution] = useState<Execution | null>(null);

  // Script data fetching
  const { script, error: scriptError, mutate, isLoading } = useScript(scriptId);
  const [isSaving, setIsSaving] = useState(false);
  const [isActive, setIsActive] = useState(true);

  // Add modal state for installation logs
  const [showInstallationLogs, setShowInstallationLogs] = useState(false);
  const [installationLogs, setInstallationLogs] = useState<string[]>([]);
  const [isInstalling, setIsInstalling] = useState(false);

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
        setIsInstalling(true);
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
        setIsInstalling(false);
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
      setIsInstalling(true);
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
      setIsInstalling(false);
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
      if (!scriptId) return;
      const executions = await scriptsApi.listExecutions(scriptId);
      setExecutions(executions);
    } catch (error) {
      console.error('Failed to load executions:', error);
    }
  };

  useEffect(() => {
    if (scriptId) {
      loadExecutions();
    }
  }, [scriptId]);

  // Add helper function to check dependency status
  const hasUninstalledDependencies = () => {
    return dependencies.some(dep => !dep.installed_version);
  };

  // Update handleRun to check dependencies first
  const handleRun = async () => {
    if (hasUninstalledDependencies()) {
      notifications.show({
        title: 'Cannot Execute Script',
        message: 'Please install all dependencies before running the script.',
        color: 'red',
      });
      return;
    }

    setIsExecuting(true);
    setExecutionOutput('');
    setExecutionStatus(ExecutionStatus.PENDING);
    setShowExecutionModal(true);

    try {
      // Execute script and get initial response
      const response = await scriptsApi.execute(scriptId);
      console.log('Execution started:', response);

      // Add detailed logging of the response
      console.log('Response details:', {
        hasResponse: !!response,
        responseType: typeof response,
        executionId: response?.execution_id,
        fullResponse: JSON.stringify(response)
      });

      // Validate response structure
      if (!response || typeof response !== 'object') {
        throw new Error('Invalid response from server');
      }

      const executionId = response.execution_id;
      if (!executionId && executionId !== 0) {  // Allow 0 as valid ID
        console.error('Invalid execution_id in response:', response);
        throw new Error('No execution ID received from server');
      }

      let retryCount = 0;
      const maxRetries = 3;
      let ws: WebSocket | null = null;

      const connectWebSocket = () => {
        if (ws) {
          ws.close();
        }

        const wsUrl = `${WS_BASE_URL}/api/scripts/${scriptId}/ws?execution_id=${executionId}`;
        console.log('Connecting WebSocket:', {
          scriptId,
          executionId,
          wsUrl
        });

        ws = new WebSocket(wsUrl);
        let isConnected = false;

        // Add connection timeout
        const connectionTimeout = setTimeout(() => {
          if (!isConnected) {
            console.log('WebSocket connection timeout');
            ws?.close();
          }
        }, 5000);

        ws.onopen = () => {
          console.log('WebSocket connected successfully');
          isConnected = true;
          clearTimeout(connectionTimeout);
          setExecutionOutput(prev => prev + 'Connected to execution stream...\n');
        };

        ws.onmessage = (event) => {
          const message = event.data;
          console.log('WebSocket message received:', message);

          if (message.startsWith('STATUS:')) {
            const status = message.split(':')[1].trim().toUpperCase() as ExecutionStatus;
            console.log('Status update received:', status);
            
            if (status === ExecutionStatus.SUCCESS || status === ExecutionStatus.FAILURE) {
              console.log('Execution completed with status:', status);
              setExecutionStatus(status);
              setIsExecuting(false);
              
              // Fetch final logs
              scriptsApi.getExecutionLogs(scriptId, executionId).then(logs => {
                if (logs) {
                  setExecutionOutput(prev => prev + logs + '\n');
                }
                const completionMessage = status === ExecutionStatus.SUCCESS 
                  ? '\nScript execution completed successfully.'
                  : '\nScript execution failed.';
                setExecutionOutput(prev => prev + completionMessage + '\n');
              }).catch(err => {
                console.error('Error fetching final logs:', err);
                const completionMessage = status === ExecutionStatus.SUCCESS 
                  ? '\nScript execution completed successfully.'
                  : '\nScript execution failed.';
                setExecutionOutput(prev => prev + completionMessage + '\n');
              }).finally(() => {
                loadExecutions();
                ws?.close();
              });
            }
          } else if (message.includes('Warning: Execution completed but output file was not created')) {
            console.log('Received completion warning, marking as success');
            setExecutionStatus(ExecutionStatus.SUCCESS);
            setIsExecuting(false);
            
            // Try to fetch any available logs
            scriptsApi.getExecutionLogs(scriptId, executionId).then(logs => {
              if (logs) {
                setExecutionOutput(prev => 
                  prev + 'Script execution completed. Output retrieved from logs:\n' + logs + '\n' +
                  '\nScript execution completed successfully.\n'
                );
              } else {
                setExecutionOutput(prev => 
                  prev + 'Script execution completed successfully, but did not generate any output.\n' +
                  'This is normal if the script does not print anything.\n' +
                  '\nScript execution completed successfully.\n'
                );
              }
            }).catch(err => {
              console.error('Error fetching logs after warning:', err);
              setExecutionOutput(prev => 
                prev + 'Script execution completed successfully, but did not generate any output.\n' +
                '\nScript execution completed successfully.\n'
              );
            }).finally(() => {
              loadExecutions();
              ws?.close();
            });
          } else {
            setExecutionOutput(prev => prev + message + '\n');
          }
        };

        ws.onerror = async (error) => {
          console.error('WebSocket error:', error);
          if (!isConnected && retryCount < maxRetries) {
            console.log(`Retrying WebSocket connection (${retryCount + 1}/${maxRetries})...`);
            retryCount++;
            clearTimeout(connectionTimeout);
            await new Promise(resolve => setTimeout(resolve, 1000));
            connectWebSocket();
          } else {
            clearTimeout(connectionTimeout);
            setIsExecuting(false);
            setExecutionStatus(ExecutionStatus.FAILURE);
            setExecutionOutput(prev => 
              prev + '\nError: Failed to establish WebSocket connection. Please check execution history for logs.\n'
            );
            ws?.close();
          }
        };

        ws.onclose = () => {
          console.log('WebSocket closed');
          clearTimeout(connectionTimeout);
          
          // If we're still executing when the connection closes unexpectedly
          if (isExecuting) {
            console.log('WebSocket closed while still executing, checking final status');
            scriptsApi.listExecutions(scriptId).then(async executions => {
              const execution = executions.find(e => e.id === executionId);
              if (execution) {
                console.log('Final execution status:', execution.status);
                setExecutionStatus(execution.status);
                setIsExecuting(false);
                
                try {
                  const logs = await scriptsApi.getExecutionLogs(scriptId, executionId);
                  if (logs) {
                    setExecutionOutput(prev => prev + logs + '\n');
                  }
                  setExecutionOutput(prev => prev + '\nScript execution completed.\n');
                } catch (err) {
                  console.error('Error fetching final logs:', err);
                }
              }
            }).catch(err => {
              console.error('Error checking final execution status:', err);
              setIsExecuting(false);
            });
          }
        };
      };

      // Initial WebSocket connection
      connectWebSocket();

    } catch (error) {
      console.error('Error executing script:', error);
      setExecutionStatus(ExecutionStatus.FAILURE);
      setIsExecuting(false);
      setExecutionOutput(prev => prev + `Error executing script: ${error}\n`);
      
      notifications.show({
        title: 'Error',
        message: 'Failed to execute script. Please check the execution output for details.',
        color: 'red',
      });
    }
  };

  const closeExecutionModal = () => {
    console.log('Closing execution modal, isExecuting:', isExecuting);
    setShowExecutionModal(false);
    setExecutionOutput('');
  };

  const handleViewLogs = async (execution: Execution) => {
    try {
      console.log('Opening log modal for execution:', execution);
      setSelectedExecution(execution);
      setLogContent('Loading logs...');
      setIsLogModalOpen(true);

      if (!scriptId) return;

      const logs = await scriptsApi.getExecutionLogs(scriptId, execution.id);
      console.log('Received logs:', logs);
      
      if (!logs && logs !== '') {
        setLogContent('No logs available');
      } else {
        // Clean logs and set content
        const cleanedLogs = logs.split('\n')
          .map(line => line.replace(/^ERROR: /, ''))
          .join('\n');
        setLogContent(cleanedLogs);
      }
    } catch (err) {
      console.error('Error loading logs:', err);
      handleApiError(err, 'loading execution logs');
      setLogContent('Error loading logs');
    }
  };

  const closeLogModal = () => {
    console.log('Closing log modal');
    setIsLogModalOpen(false);
    setSelectedExecution(null);
    setLogContent('');
  };

  // Add effect to monitor modal state
  useEffect(() => {
    console.log('Modal state changed - isLogModalOpen:', isLogModalOpen);
  }, [isLogModalOpen]);

  const handleInstallDependencies = async () => {
    try {
      setIsInstalling(true);
      setShowInstallationLogs(true);
      setInstallationLogs([]);

      // Start the installation
      await scriptsApi.installDependencies(Number(id));

      // Setup WebSocket connection for real-time logs
      const ws = new WebSocket(`${WS_BASE_URL}/api/scripts/${id}/dependencies/ws`);

      ws.onmessage = (event) => {
        const message = event.data;
        setInstallationLogs(prev => [...prev, message]);
        
        // Check for installation completion message
        if (message.includes('Installation finished.')) {
          setIsInstalling(false);
          // Refresh script data to show updated dependencies
          mutate();
        }
      };

      ws.onclose = () => {
        console.log('WebSocket connection closed');
      };

      ws.onerror = (error) => {
        console.error('WebSocket error:', error);
        notifications.show({
          title: 'Error',
          message: 'Failed to connect to log stream',
          color: 'red',
        });
        setIsInstalling(false);
      };
    } catch (error) {
      console.error('Failed to install dependencies:', error);
      notifications.show({
        title: 'Error',
        message: 'Failed to start dependency installation',
        color: 'red',
      });
      setIsInstalling(false);
    }
  };

  // Update handleToggleActive to use the helper function
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
        if (hasUninstalledDependencies()) {
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

  // Update isToggleDisabled to use the helper function
  const isToggleDisabled = () => {
    if (!script) return true;
    if (isActive) return false; // Can always disable
    return !script.schedules.length || hasUninstalledDependencies();
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
      navigate('/');
    } catch (err) {
      handleApiError(err, 'deleting script');
    } finally {
      setIsDeleting(false);
      setIsDeleteModalOpen(false);
    }
  };

  // Add this useEffect after the handleRun function
  useEffect(() => {
    const outputElement = document.querySelector('.execution-output');
    if (outputElement) {
      outputElement.scrollTop = outputElement.scrollHeight;
    }
  }, [executionOutput]);

  if (isLoading) return <LoadingOverlay visible />;
  if (scriptError) return <Text c="red">Error loading script: {scriptError.message}</Text>;

  return (
    <Box p="xl" pos="relative">
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
              leftSection={isExecuting ? <IconLoader2 className="rotating" /> : <IconPlayerPlay />}
              onClick={handleRun}
              loading={isExecuting}
              disabled={isExecuting || hasUninstalledDependencies()}
            >
              {hasUninstalledDependencies() ? 'Install Dependencies First' : 'Run Script'}
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
          <Stack gap="xl" style={{ flex: 1 }}>
            {/* Dependencies */}
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
                    loading={isInstalling}
                    disabled={!hasUninstalledDependencies() || isInstalling}
                  >
                    Install Dependencies
                  </Button>
                </Group>
              </Stack>
            </Card>

            {/* Code Editor */}
            <Card withBorder>
              <Text fw={500} size="lg" mb="md">Content</Text>
              <div style={{ 
                position: 'relative',
                minHeight: '600px',
                width: '100%'
              }}>
                <CodeEditor
                  value={content}
                  onChange={handleContentChange}
                  height="600px"
                />
              </div>
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
              </Group>

              {executions.length > 0 ? (
                <Table>
                  <Table.Thead>
                    <Table.Tr>
                      <Table.Th>Status</Table.Th>
                      <Table.Th>Started</Table.Th>
                      <Table.Th>Completed</Table.Th>
                      <Table.Th>Actions</Table.Th>
                    </Table.Tr>
                  </Table.Thead>
                  <Table.Tbody>
                    {executions.map((execution) => (
                      <Table.Tr key={execution.id}>
                        <Table.Td>
                          <Badge
                            color={
                              execution.status === ExecutionStatus.SUCCESS
                                ? 'green'
                                : execution.status === ExecutionStatus.FAILURE
                                ? 'red'
                                : execution.status === ExecutionStatus.RUNNING
                                ? 'blue'
                                : 'gray'
                            }
                            leftSection={
                              execution.status === ExecutionStatus.SUCCESS ? (
                                <IconCheck size={14} />
                              ) : execution.status === ExecutionStatus.FAILURE ? (
                                <IconX size={14} />
                              ) : execution.status === ExecutionStatus.RUNNING ? (
                                <IconLoader2 size={14} className="rotating" />
                              ) : (
                                <IconClock size={14} />
                              )
                            }
                          >
                            {execution.status}
                          </Badge>
                        </Table.Td>
                        <Table.Td>{formatDate(execution.started_at)}</Table.Td>
                        <Table.Td>
                          {execution.completed_at
                            ? formatDate(execution.completed_at)
                            : '-'}
                        </Table.Td>
                        <Table.Td>
                          <Button
                            variant="light"
                            size="xs"
                            onClick={() => handleViewLogs(execution)}
                          >
                            View Logs
                          </Button>
                        </Table.Td>
                      </Table.Tr>
                    ))}
                  </Table.Tbody>
                </Table>
              ) : (
                <Text c="dimmed" ta="center">No executions yet</Text>
              )}
            </Card>
          </Stack>
        </div>
      </Stack>

      {/* Execution Modal */}
      {showExecutionModal && (
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
                  <Group>
                    <Title order={3}>Script Execution</Title>
                    <Badge
                      color={
                        executionStatus === ExecutionStatus.SUCCESS
                          ? 'green'
                          : executionStatus === ExecutionStatus.FAILURE
                          ? 'red'
                          : executionStatus === ExecutionStatus.RUNNING
                          ? 'blue'
                          : 'gray'
                      }
                      leftSection={
                        executionStatus === ExecutionStatus.SUCCESS ? (
                          <IconCheck size={14} />
                        ) : executionStatus === ExecutionStatus.FAILURE ? (
                          <IconX size={14} />
                        ) : executionStatus === ExecutionStatus.RUNNING ? (
                          <IconLoader2 size={14} className="rotating" />
                        ) : (
                          <IconClock size={14} />
                        )
                      }
                    >
                      {executionStatus}
                    </Badge>
                  </Group>
                  <ActionIcon 
                    onClick={closeExecutionModal} 
                    disabled={isExecuting}
                    variant="subtle"
                  >
                    ✕
                  </ActionIcon>
                </Group>

                <Paper
                  className="execution-output"
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
                  {executionOutput ? (
                    executionOutput.split('\n').map((line, index) => (
                      <Text
                        key={index}
                        style={{
                          whiteSpace: 'pre-wrap',
                          color: '#d4d4d4',
                          padding: '2px 0',
                          fontSize: 'inherit',
                        }}
                      >
                        {line}
                      </Text>
                    ))
                  ) : (
                    <Text c="dimmed" ta="center">
                      {isExecuting ? 'Executing script...' : 'Waiting for output...'}
                    </Text>
                  )}
                </Paper>

                <Group justify="flex-end">
                  <Button
                    variant="light"
                    color="gray"
                    onClick={closeExecutionModal}
                    disabled={isExecuting}
                  >
                    Close
                  </Button>
                </Group>
              </Stack>
            </Paper>
          </div>
        </Portal>
      )}

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

      {/* Delete Confirmation Modal */}
      {isDeleteModalOpen && (
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
                maxWidth: '500px',
                margin: '20px',
                position: 'relative',
              }}
              p="md"
            >
              <Stack>
                <Group justify="space-between" mb="md">
                  <Title order={3}>Delete Script</Title>
                  <ActionIcon 
                    onClick={() => setIsDeleteModalOpen(false)}
                    variant="subtle"
                    disabled={isDeleting}
                  >
                    ✕
                  </ActionIcon>
                </Group>

                <Text>Are you sure you want to delete this script? This action cannot be undone.</Text>

                <Group justify="flex-end">
                  <Button
                    variant="light"
                    onClick={() => setIsDeleteModalOpen(false)}
                    disabled={isDeleting}
                  >
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
            </Paper>
          </div>
        </Portal>
      )}

      {/* Installation Logs Modal */}
      {showInstallationLogs && (
        <Portal>
          <div
            style={{
              position: 'fixed',
              top: 0,
              left: 0,
              right: 0,
              bottom: 0,
              background: 'rgba(0, 0, 0, 0.75)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              zIndex: 1000,
            }}
          >
            <Paper
              style={{
                width: '90%',
                maxWidth: '800px',
                margin: '20px',
                position: 'relative',
              }}
              p="md"
            >
              <Stack>
                <Group justify="space-between" mb="md">
                  <Title order={3}>Installing Dependencies</Title>
                  <ActionIcon 
                    onClick={() => !isInstalling && setShowInstallationLogs(false)}
                    variant="subtle"
                    disabled={isInstalling}
                  >
                    ✕
                  </ActionIcon>
                </Group>

                <ScrollArea h={400} type="auto">
                  <Code block style={{ whiteSpace: 'pre-wrap', background: '#1A1B1E' }}>
                    {installationLogs.join('\n')}
                  </Code>
                </ScrollArea>

                <Group justify="flex-end">
                  <Button
                    variant="light"
                    onClick={() => setShowInstallationLogs(false)}
                    disabled={isInstalling}
                  >
                    Close
                  </Button>
                </Group>
              </Stack>
            </Paper>
          </div>
        </Portal>
      )}
    </Box>
  );
} 
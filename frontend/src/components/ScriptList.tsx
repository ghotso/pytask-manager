import { useEffect, useState } from 'react';
import {
  Card,
  Text,
  Group,
  Stack,
  Badge,
  Button,
  TextInput,
  LoadingOverlay,
  Box,
  Title,
  Switch,
  Tooltip,
} from '@mantine/core';
import { notifications } from '@mantine/notifications';
import { Link } from 'react-router-dom';
import { 
  IconPlus, 
  IconSearch, 
  IconAlertTriangle,
  IconCheck,
  IconX,
} from '@tabler/icons-react';
import { scriptsApi } from '../api/client';
import { Script, Dependency, ExecutionStatus } from '../types';

export function ScriptList() {
  const [scripts, setScripts] = useState<Script[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');

  const loadScripts = async (isInitialLoad = false) => {
    try {
      if (isInitialLoad) {
        setIsLoading(true);
      }
      
      const data = await scriptsApi.list();
      setScripts(data);
    } catch (error) {
      console.error('Failed to load scripts:', error);
      if (isInitialLoad) {
        notifications.show({
          title: 'Error',
          message: 'Failed to load scripts',
          color: 'red',
        });
      }
    } finally {
      if (isInitialLoad) {
        setIsLoading(false);
      }
    }
  };

  useEffect(() => {
    loadScripts(true);
    const interval = setInterval(() => loadScripts(false), 5000);
    return () => clearInterval(interval);
  }, []);

  const filteredScripts = scripts.filter(script => {
    const searchLower = searchQuery.toLowerCase();
    return (
      script.name.toLowerCase().includes(searchLower) ||
      script.tags.some(tag => tag.name.toLowerCase().includes(searchLower))
    );
  });

  const isToggleDisabled = (script: Script) => {
    if (script.is_active) return false; // Can always disable
    return (
      !script.schedules.length || // No schedules
      script.dependencies.some(dep => !dep.installed_version) // Uninstalled deps
    );
  };

  const getToggleTooltip = (script: Script) => {
    if (script.is_active) return "Click to disable scheduled executions";
    if (!script.schedules.length) return "Cannot enable: No schedules defined";
    if (script.dependencies.some(dep => !dep.installed_version)) {
      return "Cannot enable: Some dependencies are not installed";
    }
    return "Click to enable scheduled executions";
  };

  const handleToggleActive = async (script: Script) => {
    try {
      // Check if we can enable the script
      if (!script.is_active) {
        // Can't enable if no schedules
        if (!script.schedules.length) {
          notifications.show({
            title: 'Error',
            message: 'Cannot enable script without any schedules',
            color: 'red',
          });
          return;
        }
        
        // Can't enable if dependencies not installed
        const hasUninstalledDeps = script.dependencies.some(
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

      const newIsActive = !script.is_active;
      await scriptsApi.update(script.id, { is_active: newIsActive });
      await loadScripts(false);
      notifications.show({
        title: 'Success',
        message: `Scheduled executions ${newIsActive ? 'enabled' : 'disabled'}`,
        color: 'green',
      });
    } catch (error) {
      console.error('Failed to toggle script status:', error);
      notifications.show({
        title: 'Error',
        message: 'Failed to update script status',
        color: 'red',
      });
    }
  };

  return (
    <Box p="xl" pos="relative">
      <LoadingOverlay visible={isLoading} />
      <Stack gap="xl">
        <Group justify="space-between" align="flex-start">
          <Title order={2}>Scripts</Title>
          <Button
            component={Link}
            to="/scripts/new"
            leftSection={<IconPlus size={16} />}
          >
            New Script
          </Button>
        </Group>

        <TextInput
          placeholder="Search scripts by name or tag..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          leftSection={<IconSearch size={16} />}
          style={{ maxWidth: '400px' }}
        />

        <div style={{ 
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fill, minmax(250px, 1fr))',
          gap: '1rem',
          width: '100%'
        }}>
          {filteredScripts.map((script) => (
            <Card
              key={script.id}
              withBorder
              style={{ 
                textDecoration: 'none', 
                color: 'inherit',
                backgroundColor: '#1A1B1E',
                transition: 'transform 0.2s ease, border-color 0.2s ease',
                '&:hover': {
                  transform: 'translateY(-2px)',
                  borderColor: 'var(--mantine-color-blue-filled)',
                }
              }}
            >
              <Stack gap="xs">
                <Group justify="space-between" align="flex-start">
                  <Text 
                    component={Link}
                    to={`/scripts/${script.id}`}
                    fw={500} 
                    size="lg" 
                    lineClamp={1}
                    style={{ 
                      textDecoration: 'none',
                      color: 'inherit',
                      flex: 1
                    }}
                  >
                    {script.name}
                  </Text>
                  <Tooltip label={getToggleTooltip(script)}>
                    <Switch
                      checked={script.is_active}
                      onChange={() => handleToggleActive(script)}
                      disabled={isToggleDisabled(script)}
                      size="md"
                      onClick={(e) => e.stopPropagation()}
                    />
                  </Tooltip>
                </Group>
                
                {script.description && (
                  <Text 
                    component={Link}
                    to={`/scripts/${script.id}`}
                    size="sm" 
                    c="dimmed" 
                    lineClamp={2}
                    style={{ 
                      textDecoration: 'none',
                      color: 'inherit'
                    }}
                  >
                    {script.description}
                  </Text>
                )}

                {script.tags.length > 0 && (
                  <Group gap="xs" mt="xs">
                    {script.tags.map((tag) => (
                      <Badge
                        key={tag.name}
                        size="sm"
                        variant="light"
                      >
                        {tag.name}
                      </Badge>
                    ))}
                  </Group>
                )}

                <Group mt="auto" pt="sm" style={{ borderTop: '1px solid #2C2E33' }}>
                  <Group gap="xs">
                    {script.dependencies.some(dep => !dep.installed_version) && (
                      <Tooltip label="Some dependencies are not installed">
                        <Badge size="sm" color="yellow" leftSection={
                          <IconAlertTriangle size={12} style={{ marginRight: 4 }} />
                        }>
                          Dependencies
                        </Badge>
                      </Tooltip>
                    )}
                    {script.schedules.length > 0 && (
                      <Badge size="sm" color="blue">
                        {script.schedules.length} Schedule{script.schedules.length !== 1 ? 's' : ''}
                      </Badge>
                    )}
                    {script.last_execution && (
                      <Tooltip label={`Last execution: ${script.last_execution.status}`}>
                        <Badge 
                          size="sm" 
                          color={script.last_execution.status === ExecutionStatus.SUCCESS ? 'green' : 'red'}
                          leftSection={
                            script.last_execution.status === ExecutionStatus.SUCCESS
                              ? <IconCheck size={12} />
                              : <IconX size={12} />
                          }
                        >
                          Last Run
                        </Badge>
                      </Tooltip>
                    )}
                  </Group>
                </Group>
              </Stack>
            </Card>
          ))}
          {!isLoading && filteredScripts.length === 0 && (
            <Text c="dimmed" ta="center" style={{ gridColumn: '1 / -1', padding: '2rem' }}>
              {searchQuery ? 'No scripts found matching your search' : 'No scripts created yet'}
            </Text>
          )}
        </div>
      </Stack>
    </Box>
  );
} 
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
  SegmentedControl,
} from '@mantine/core';
import { notifications } from '@mantine/notifications';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { 
  IconPlus, 
  IconSearch, 
  IconAlertTriangle,
  IconCheck,
  IconX,
} from '@tabler/icons-react';
import { scriptsApi } from '../api/client';
import { Script, Dependency, ExecutionStatus } from '../types';

type FilterType = 'all' | 'active' | 'inactive' | 'failed' | 'missing-deps';

export function ScriptList() {
  const location = useLocation();
  const navigate = useNavigate();
  const [scripts, setScripts] = useState<Script[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [filter, setFilter] = useState<FilterType>('all');

  // Parse filter from URL search params
  useEffect(() => {
    const params = new URLSearchParams(location.search);
    const filterParam = params.get('filter') as FilterType;
    if (filterParam && ['all', 'active', 'inactive', 'failed', 'missing-deps'].includes(filterParam)) {
      setFilter(filterParam);
    }
  }, [location.search]);

  const loadScripts = async (isInitialLoad = false) => {
    try {
      if (isInitialLoad) {
        setIsLoading(true);
      }
      
      const data = await scriptsApi.list();
      
      // Ensure last_execution is properly loaded for each script
      const scriptsWithExecutions = await Promise.all(
        data.map(async (script) => {
          try {
            const executions = await scriptsApi.listExecutions(script.id, 1);
            return {
              ...script,
              last_execution: executions[0] || null
            };
          } catch (error) {
            console.error(`Failed to load executions for script ${script.id}:`, error);
            return script;
          }
        })
      );
      
      setScripts(scriptsWithExecutions);
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
    
    const interval = setInterval(() => {
      loadScripts(false);
    }, 5000);
    
    return () => clearInterval(interval);
  }, []);

  const handleFilterChange = (value: FilterType) => {
    setFilter(value);
    // Update URL with new filter
    const params = new URLSearchParams(location.search);
    params.set('filter', value);
    navigate({ search: params.toString() });
  };

  const filteredScripts = scripts.filter(script => {
    // First apply search filter
    const searchLower = searchQuery.toLowerCase();
    const matchesSearch = script.name.toLowerCase().includes(searchLower) ||
      script.tags.some(tag => tag.name.toLowerCase().includes(searchLower));

    if (!matchesSearch) return false;

    // Then apply status filter
    switch (filter) {
      case 'active':
        return script.is_active;
      case 'inactive':
        return !script.is_active;
      case 'failed':
        return script.last_execution && script.last_execution.status === ExecutionStatus.FAILURE;
      case 'missing-deps':
        return script.dependencies.some(dep => !dep.installed_version);
      default:
        return true;
    }
  });

  const isToggleDisabled = (script: Script) => {
    if (script.is_active) return false;
    return (
      !script.schedules.length ||
      script.dependencies.some(dep => !dep.installed_version)
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
      if (!script.is_active) {
        if (!script.schedules.length) {
          notifications.show({
            title: 'Error',
            message: 'Cannot enable script without any schedules',
            color: 'red',
          });
          return;
        }
        
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

        <Group align="flex-start">
          <TextInput
            placeholder="Search scripts by name or tag..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            leftSection={<IconSearch size={16} />}
            style={{ maxWidth: '400px' }}
          />
          
          <SegmentedControl
            value={filter}
            onChange={(value) => handleFilterChange(value as FilterType)}
            data={[
              { label: 'All', value: 'all' },
              { label: 'Active', value: 'active' },
              { label: 'Inactive', value: 'inactive' },
              { label: 'Failed', value: 'failed' },
              { label: 'Missing Dependencies', value: 'missing-deps' },
            ]}
          />
        </Group>

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
              padding="md"
              style={{ 
                textDecoration: 'none', 
                color: 'inherit',
                backgroundColor: script.is_active ? 'rgba(59, 130, 246, 0.1)' : 'rgba(234, 179, 8, 0.1)',
                borderColor: script.is_active ? 'rgba(59, 130, 246, 0.2)' : 'rgba(234, 179, 8, 0.2)',
                transition: 'all 0.2s ease',
                '&:hover': {
                  transform: 'translateY(-4px)',
                  backgroundColor: script.is_active ? 'rgba(59, 130, 246, 0.15)' : 'rgba(234, 179, 8, 0.15)',
                  borderColor: script.is_active ? 'rgba(59, 130, 246, 0.3)' : 'rgba(234, 179, 8, 0.3)',
                }
              }}
            >
              <Stack gap="sm">
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
                      flex: 1,
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
                      color: 'inherit',
                      fontSize: '0.9rem',
                    }}
                  >
                    {script.description}
                  </Text>
                )}

                {script.tags.length > 0 && (
                  <Group gap="xs">
                    {script.tags.map((tag) => (
                      <Badge
                        key={tag.name}
                        size="sm"
                        variant="light"
                        style={{
                          backgroundColor: 'rgba(59, 130, 246, 0.1)',
                          color: '#fff'
                        }}
                      >
                        {tag.name}
                      </Badge>
                    ))}
                  </Group>
                )}

                <Group mt="xs" pt="xs" style={{ borderTop: '1px solid rgba(44, 46, 51, 0.5)' }}>
                  <Group gap="xs">
                    {script.dependencies.some(dep => !dep.installed_version) && (
                      <Tooltip label="Some dependencies are not installed">
                        <Badge 
                          size="sm" 
                          color="yellow" 
                          leftSection={
                            <IconAlertTriangle 
                              size={14} 
                              style={{ 
                                marginRight: 4,
                                filter: 'drop-shadow(0 0 8px rgba(234, 179, 8, 0.4))'
                              }} 
                            />
                          }
                          style={{
                            backgroundColor: 'rgba(234, 179, 8, 0.1)',
                            border: '1px solid rgba(234, 179, 8, 0.2)'
                          }}
                        >
                          Dependencies
                        </Badge>
                      </Tooltip>
                    )}
                    {script.schedules.length > 0 && (
                      <Badge 
                        size="sm" 
                        color="blue"
                        style={{
                          backgroundColor: 'rgba(59, 130, 246, 0.1)',
                          border: '1px solid rgba(59, 130, 246, 0.2)'
                        }}
                      >
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
                              ? <IconCheck size={14} style={{ filter: 'drop-shadow(0 0 8px rgba(34, 197, 94, 0.4))' }} />
                              : <IconX size={14} style={{ filter: 'drop-shadow(0 0 8px rgba(239, 68, 68, 0.4))' }} />
                          }
                          style={{
                            backgroundColor: script.last_execution.status === ExecutionStatus.SUCCESS 
                              ? 'rgba(34, 197, 94, 0.1)'
                              : 'rgba(239, 68, 68, 0.1)',
                            border: script.last_execution.status === ExecutionStatus.SUCCESS
                              ? '1px solid rgba(34, 197, 94, 0.2)'
                              : '1px solid rgba(239, 68, 68, 0.2)'
                          }}
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
              {searchQuery || filter !== 'all' ? 'No scripts found matching your criteria' : 'No scripts created yet'}
            </Text>
          )}
        </div>
      </Stack>
    </Box>
  );
} 
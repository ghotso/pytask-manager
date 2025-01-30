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
} from '@mantine/core';
import { notifications } from '@mantine/notifications';
import { Link } from 'react-router-dom';
import { IconPlus, IconSearch } from '@tabler/icons-react';
import { scriptsApi } from '../api/client';
import { Script } from '../types';

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
              component={Link}
              to={`/scripts/${script.id}`}
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
                <Text fw={500} size="lg" lineClamp={1}>
                  {script.name}
                </Text>
                
                {script.description && (
                  <Text size="sm" c="dimmed" lineClamp={2}>
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
                    <Badge
                      size="sm"
                      color={script.is_active ? 'green' : 'gray'}
                    >
                      {script.is_active ? 'Active' : 'Inactive'}
                    </Badge>
                    {script.schedules.length > 0 && (
                      <Badge size="sm" color="blue">
                        {script.schedules.length} Schedule{script.schedules.length !== 1 ? 's' : ''}
                      </Badge>
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
import { useState } from 'react';
import {
  Box,
  TextInput,
  Group,
  Button,
  Stack,
  Text,
  Card,
} from '@mantine/core';
import { notifications } from '@mantine/notifications';
import { useNavigate } from 'react-router-dom';
import { CodeEditor } from './CodeEditor';
import { TagInput } from './TagInput';
import { DependencyInput } from './DependencyInput';
import { ScheduleInput } from './ScheduleInput';
import { scriptsApi } from '../api/client';
import { Tag, Dependency, Schedule } from '../types';

export function ScriptForm() {
  const navigate = useNavigate();
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [content, setContent] = useState('');
  const [tags, setTags] = useState<Tag[]>([]);
  const [dependencies, setDependencies] = useState<Dependency[]>([]);
  const [schedules, setSchedules] = useState<Schedule[]>([]);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleSubmit = async () => {
    if (!name.trim()) {
      notifications.show({
        title: 'Error',
        message: 'Script name is required',
        color: 'red',
      });
      return;
    }

    setIsSubmitting(true);
    try {
      const createData = {
        name,
        description,
        content,
        tags: tags.map(tag => tag.name),
        dependencies: dependencies.map(dep => ({
          package_name: dep.package_name,
          version_spec: dep.version_spec,
        })),
        schedules: schedules.map(schedule => ({
          cron_expression: schedule.cron_expression,
          description: schedule.description,
        })),
        is_active: false,
      };

      const response = await scriptsApi.create(createData);
      notifications.show({
        title: 'Success',
        message: 'Script created successfully',
        color: 'green',
      });
      navigate(`/scripts/${response.id}`);
    } catch (error) {
      console.error('Error creating script:', error);
      notifications.show({
        title: 'Error',
        message: 'Failed to create script',
        color: 'red',
      });
    } finally {
      setIsSubmitting(false);
    }
  };

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
                onChange={(e) => setName(e.target.value)}
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
                onChange={(e) => setDescription(e.target.value)}
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
            <Button
              onClick={() => navigate('/')}
              variant="light"
            >
              Cancel
            </Button>
            <Button
              onClick={handleSubmit}
              loading={isSubmitting}
            >
              Create Script
            </Button>
          </Group>
        </Group>
        
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
                  onChange={setDependencies}
                />
                
                <Box style={{ overflowX: 'auto', backgroundColor: '#1A1B1E', border: '1px solid #2C2E33', borderRadius: '4px' }}>
                  {dependencies.length === 0 ? (
                    <Text c="dimmed" ta="center" py="xl">
                      No dependencies defined
                    </Text>
                  ) : (
                    <div style={{ padding: '1rem' }}>
                      {dependencies.map((dep) => (
                        <Group key={dep.package_name} justify="space-between" mb="xs">
                          <Text>{dep.package_name}</Text>
                          <Text c="dimmed">{dep.version_spec || 'latest'}</Text>
                        </Group>
                      ))}
                    </div>
                  )}
                </Box>
              </Stack>
            </Card>

            <Card withBorder>
              <Text fw={500} size="lg" mb="md">Content</Text>
              <CodeEditor
                value={content}
                onChange={setContent}
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
                onChange={setTags}
              />
            </Card>

            <Card withBorder>
              <Text fw={500} size="lg" mb="md">Schedules</Text>
              <ScheduleInput
                value={schedules}
                onChange={setSchedules}
              />
            </Card>
          </Stack>
        </div>
      </Stack>
    </Box>
  );
} 
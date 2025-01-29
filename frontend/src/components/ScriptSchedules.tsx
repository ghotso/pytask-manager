import {
  ActionIcon,
  Button,
  Card,
  Group,
  Modal,
  Stack,
  Text,
  TextInput,
  Title,
} from '@mantine/core';
import { useForm } from '@mantine/form';
import { useDisclosure } from '@mantine/hooks';
import { notifications } from '@mantine/notifications';
import { IconEdit, IconTrash } from '@tabler/icons-react';
import { useEffect, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import {
  CreateScheduleData,
  Schedule,
  Script,
  UpdateScheduleData,
  schedulesApi,
  scriptsApi,
} from '../api/client';
import { Schedule as ScheduleType } from '../types';

export function ScriptSchedules() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [script, setScript] = useState<Script | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [selectedSchedule, setSelectedSchedule] = useState<Schedule | null>(null);
  const [opened, { open, close }] = useDisclosure(false);

  const form = useForm<CreateScheduleData>({
    initialValues: {
      cron_expression: '',
      description: '',
    },
  });

  useEffect(() => {
    if (id) {
      loadScript(parseInt(id));
    }
  }, [id]);

  const loadScript = async (scriptId: number) => {
    try {
      const data = await scriptsApi.get(scriptId);
      setScript(data);
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

  const handleSubmit = async (values: CreateScheduleData) => {
    if (!id) return;

    try {
      if (selectedSchedule) {
        if (!selectedSchedule.id) {
          throw new Error('Schedule ID is missing');
        }
        await schedulesApi.update(
          parseInt(id),
          selectedSchedule.id,
          values as UpdateScheduleData,
        );
        notifications.show({
          title: 'Success',
          message: 'Schedule updated successfully',
          color: 'green',
        });
      } else {
        await schedulesApi.create(parseInt(id), values);
        notifications.show({
          title: 'Success',
          message: 'Schedule created successfully',
          color: 'green',
        });
      }
      close();
      loadScript(parseInt(id));
    } catch (error) {
      notifications.show({
        title: 'Error',
        message: 'Failed to save schedule',
        color: 'red',
      });
    }
  };

  const handleEdit = (schedule: Schedule) => {
    setSelectedSchedule(schedule);
    form.setValues({
      cron_expression: schedule.cron_expression,
      description: schedule.description || '',
    });
    open();
  };

  const handleDelete = async (schedule: Schedule) => {
    if (!id || !schedule.id) return;

    try {
      await schedulesApi.delete(parseInt(id), schedule.id);
      notifications.show({
        title: 'Success',
        message: 'Schedule deleted successfully',
        color: 'green',
      });
      loadScript(parseInt(id));
    } catch (error) {
      notifications.show({
        title: 'Error',
        message: 'Failed to delete schedule',
        color: 'red',
      });
    }
  };

  const handleOpenModal = () => {
    setSelectedSchedule(null);
    form.reset();
    open();
  };

  if (isLoading || !script) {
    return null;
  }

  return (
    <>
      <Stack>
        <Group justify="space-between">
          <Stack gap={0}>
            <Title order={2}>Schedules</Title>
            <Text c="dimmed">{script.name}</Text>
          </Stack>

          <Group>
            <Button variant="light" onClick={() => navigate('/')}>
              Back
            </Button>
            <Button onClick={handleOpenModal}>New Schedule</Button>
          </Group>
        </Group>

        <Stack>
          {script.schedules?.map((schedule: ScheduleType) => (
            <Card key={schedule.id} withBorder>
              <Group justify="space-between">
                <Stack gap="xs">
                  <Group>
                    <Text fw={500}>{schedule.cron_expression}</Text>
                  </Group>
                  {schedule.description && (
                    <Text size="sm" c="dimmed">
                      {schedule.description}
                    </Text>
                  )}
                </Stack>

                <Group>
                  <ActionIcon
                    variant="light"
                    onClick={() => handleEdit(schedule)}
                    title="Edit"
                  >
                    <IconEdit size={18} />
                  </ActionIcon>
                  <ActionIcon
                    variant="light"
                    color="red"
                    onClick={() => handleDelete(schedule)}
                    title="Delete"
                  >
                    <IconTrash size={18} />
                  </ActionIcon>
                </Group>
              </Group>
            </Card>
          ))}

          {script.schedules?.length === 0 && (
            <Text ta="center" c="dimmed">
              No schedules found. Create one to get started!
            </Text>
          )}
        </Stack>
      </Stack>

      <Modal
        opened={opened}
        onClose={close}
        title={selectedSchedule ? 'Edit Schedule' : 'New Schedule'}
      >
        <form onSubmit={form.onSubmit(handleSubmit)}>
          <Stack>
            <TextInput
              label="Cron Expression"
              placeholder="* * * * *"
              required
              {...form.getInputProps('cron_expression')}
            />

            <TextInput
              label="Description"
              placeholder="Enter schedule description"
              {...form.getInputProps('description')}
            />

            <Group justify="flex-end">
              <Button variant="light" onClick={close}>
                Cancel
              </Button>
              <Button type="submit">
                {selectedSchedule ? 'Update' : 'Create'} Schedule
              </Button>
            </Group>
          </Stack>
        </form>
      </Modal>
    </>
  );
} 
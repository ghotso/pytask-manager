import { ReactElement } from 'react';
import { Schedule } from '../types';
import { TextInput, Button, Stack, Group, ActionIcon, Text } from '@mantine/core';
import { IconTrash } from '@tabler/icons-react';
import cronstrue from 'cronstrue';

interface ScheduleInputProps {
  value: Schedule[];
  onChange: (schedules: Schedule[]) => void;
}

export function ScheduleInput({ value, onChange }: ScheduleInputProps): ReactElement {
  const handleAdd = () => {
    onChange([...value, { cron_expression: '', description: '' }]);
  };

  const handleRemove = (index: number) => {
    onChange(value.filter((_, i) => i !== index));
  };

  const handleChange = (index: number, field: keyof Schedule, newValue: string) => {
    onChange(
      value.map((schedule, i) =>
        i === index ? { ...schedule, [field]: newValue } : schedule
      )
    );
  };

  const getCronDescription = (cronExpression: string): string => {
    try {
      return cronExpression ? cronstrue.toString(cronExpression) : '';
    } catch {
      return '';
    }
  };

  return (
    <Stack gap="md">
      {value.map((schedule, index) => (
        <Stack key={index} gap="xs">
          <Group gap="sm">
            <TextInput
              placeholder="Cron Expression (e.g., * * * * *)"
              style={{ flex: 1 }}
              value={schedule.cron_expression}
              onChange={(e) =>
                handleChange(index, 'cron_expression', e.target.value)
              }
            />
            <ActionIcon
              variant="subtle"
              color="red"
              onClick={() => handleRemove(index)}
            >
              <IconTrash size={16} />
            </ActionIcon>
          </Group>
          {schedule.cron_expression && (
            <Text size="sm" c="dimmed" style={{ marginTop: '-8px' }}>
              {getCronDescription(schedule.cron_expression)}
            </Text>
          )}
          <TextInput
            placeholder="Description (optional)"
            value={schedule.description || ''}
            onChange={(e) => handleChange(index, 'description', e.target.value)}
          />
        </Stack>
      ))}
      <Button variant="light" onClick={handleAdd}>
        Add Schedule
      </Button>
    </Stack>
  );
} 
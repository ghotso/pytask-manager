import { ReactElement } from 'react';
import { Schedule } from '../types';
import { TextInput, Button, Stack, ActionIcon, Text, Table } from '@mantine/core';
import { IconTrash } from '@tabler/icons-react';
import cronstrue from 'cronstrue';

interface ScheduleInputProps {
  value: Schedule[];
  onChange: (schedules: Schedule[]) => void;
}

export function ScheduleInput({ value, onChange }: ScheduleInputProps): ReactElement {
  const handleAdd = () => {
    onChange([...value, { cron_expression: '' }]);
  };

  const handleRemove = (index: number) => {
    onChange(value.filter((_, i) => i !== index));
  };

  const handleChange = (index: number, newValue: string) => {
    onChange(
      value.map((schedule, i) =>
        i === index ? { ...schedule, cron_expression: newValue } : schedule
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
      {value.length > 0 ? (
        <Table>
          <Table.Thead>
            <Table.Tr>
              <Table.Th>Cron Expression</Table.Th>
              <Table.Th>Description</Table.Th>
              <Table.Th style={{ width: 80 }}></Table.Th>
            </Table.Tr>
          </Table.Thead>
          <Table.Tbody>
            {value.map((schedule, index) => (
              <Table.Tr key={index}>
                <Table.Td>
                  <TextInput
                    placeholder="e.g., * * * * *"
                    value={schedule.cron_expression}
                    onChange={(e) => handleChange(index, e.target.value)}
                  />
                </Table.Td>
                <Table.Td>
                  <Text size="sm" c={schedule.cron_expression ? undefined : "dimmed"}>
                    {schedule.cron_expression ? 
                      getCronDescription(schedule.cron_expression) : 
                      'Enter a cron expression'}
                  </Text>
                </Table.Td>
                <Table.Td>
                  <ActionIcon
                    variant="subtle"
                    color="red"
                    onClick={() => handleRemove(index)}
                  >
                    <IconTrash size={16} />
                  </ActionIcon>
                </Table.Td>
              </Table.Tr>
            ))}
          </Table.Tbody>
        </Table>
      ) : (
        <Text c="dimmed" ta="center" py="xl">
          No schedules configured
        </Text>
      )}
      
      <Button variant="light" onClick={handleAdd}>
        Add Schedule
      </Button>
    </Stack>
  );
} 
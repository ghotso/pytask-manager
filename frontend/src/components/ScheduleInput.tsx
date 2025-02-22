import { ReactElement } from 'react';
import { Schedule } from '../types';
import { Stack, Text, Table } from '@mantine/core';
import { ListInput } from './common/ListInput';
import cronstrue from 'cronstrue';

interface ScheduleInputProps {
  value: Schedule[];
  onChange: (schedules: Schedule[]) => void;
}

export function ScheduleInput({ value, onChange }: ScheduleInputProps): ReactElement {
  const validateCronExpression = (cronExpression: string): boolean => {
    try {
      cronstrue.toString(cronExpression);
      return true;
    } catch {
      return false;
    }
  };

  const getCronDescription = (cronExpression: string): string => {
    try {
      return cronstrue.toString(cronExpression);
    } catch {
      return 'Invalid cron expression';
    }
  };

  return (
    <Stack gap="md">
      <ListInput<Schedule>
        value={value}
        onChange={onChange}
        createItem={(cronExpression) => ({ cron_expression: cronExpression })}
        getItemLabel={(schedule) => schedule.cron_expression}
        placeholder="Enter cron expression (e.g. * * * * *)"
        validate={validateCronExpression}
      />

      {value.length > 0 && (
        <Table>
          <Table.Thead>
            <Table.Tr>
              <Table.Th>Cron Expression</Table.Th>
              <Table.Th>Description</Table.Th>
            </Table.Tr>
          </Table.Thead>
          <Table.Tbody>
            {value.map((schedule, index) => (
              <Table.Tr key={index}>
                <Table.Td>
                  <Text>{schedule.cron_expression}</Text>
                </Table.Td>
                <Table.Td>
                  <Text size="sm" c={schedule.cron_expression ? undefined : "dimmed"}>
                    {getCronDescription(schedule.cron_expression)}
                  </Text>
                </Table.Td>
              </Table.Tr>
            ))}
          </Table.Tbody>
        </Table>
      )}
    </Stack>
  );
} 
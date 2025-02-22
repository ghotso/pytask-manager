import { ReactElement } from 'react';
import { Schedule } from '../types';
import { Stack, Text, Table, Button, TextInput, Group } from '@mantine/core';
import { IconTrash } from '@tabler/icons-react';
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

  const handleAddSchedule = (input: string) => {
    if (validateCronExpression(input)) {
      onChange([...value, { cron_expression: input }]);
    }
  };

  const handleRemoveSchedule = (cronExpression: string) => {
    onChange(value.filter(schedule => schedule.cron_expression !== cronExpression));
  };

  return (
    <Stack gap="md">
      <Group>
        <TextInput
          placeholder="Enter cron expression (e.g. * * * * *)"
          style={{ flex: 1 }}
          onKeyDown={(e) => {
            if (e.key === 'Enter') {
              handleAddSchedule(e.currentTarget.value);
              e.currentTarget.value = '';
            }
          }}
        />
      </Group>

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
          <col style={{ width: '30%' }} />
          <col style={{ width: '60%' }} />
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
            }}>Cron Expression</th>
            <th style={{ 
              padding: '12px 16px',
              color: '#C1C2C5',
              fontWeight: 600,
              fontSize: '0.9rem',
              textAlign: 'left',
              borderBottom: '1px solid #2C2E33',
              backgroundColor: '#141517'
            }}>Description</th>
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
          {value.map((schedule) => (
            <tr key={schedule.cron_expression} style={{ backgroundColor: '#1A1B1E' }}>
              <td style={{ 
                padding: '12px 16px',
                color: '#C1C2C5',
                borderBottom: '1px solid #2C2E33',
                overflow: 'hidden',
                textOverflow: 'ellipsis',
                whiteSpace: 'nowrap'
              }}>
                {schedule.cron_expression}
              </td>
              <td style={{ 
                padding: '12px 16px',
                color: '#C1C2C5',
                borderBottom: '1px solid #2C2E33'
              }}>
                <Text size="sm">
                  {getCronDescription(schedule.cron_expression)}
                </Text>
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
                  onClick={() => handleRemoveSchedule(schedule.cron_expression)}
                  style={{ minWidth: 'unset' }}
                >
                  <IconTrash size={18} />
                </Button>
              </td>
            </tr>
          ))}
          {value.length === 0 && (
            <tr style={{ backgroundColor: '#1A1B1E' }}>
              <td 
                colSpan={3} 
                style={{ 
                  padding: '12px 16px',
                  color: '#666',
                  textAlign: 'center',
                  borderBottom: '1px solid #2C2E33'
                }}
              >
                No schedules defined
              </td>
            </tr>
          )}
        </tbody>
      </Table>
    </Stack>
  );
} 
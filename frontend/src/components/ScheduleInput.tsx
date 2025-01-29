import { ReactElement } from 'react';
import { ListInput } from './common/ListInput';
import { Schedule } from '../types';

interface ScheduleInputProps {
  value: Schedule[];
  onChange: (schedules: Schedule[]) => void;
}

export function ScheduleInput({ value, onChange }: ScheduleInputProps): ReactElement {
  const validateCron = (input: string) => {
    // Basic cron validation (5 or 6 fields)
    const fields = input.trim().split(/\s+/);
    return fields.length === 5 || fields.length === 6;
  };

  const createSchedule = (input: string): Schedule => ({
    cron_expression: input,
  });

  return (
    <ListInput<Schedule>
      value={value}
      onChange={onChange}
      createItem={createSchedule}
      getItemLabel={(schedule) => schedule.cron_expression}
      placeholder="Enter cron expression (e.g. * * * * *)"
      validate={validateCron}
    />
  );
} 
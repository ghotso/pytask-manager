import { ReactElement, useState } from 'react';
import { TextInput, ActionIcon, Group, Box, Pill } from '@mantine/core';
import { IconPlus } from '@tabler/icons-react';

interface ListInputProps<T> {
  value: T[];
  onChange: (items: T[]) => void;
  createItem: (input: string) => T;
  getItemLabel: (item: T) => string;
  placeholder: string;
  validate?: (input: string) => boolean;
}

export function ListInput<T>({ 
  value, 
  onChange, 
  createItem, 
  getItemLabel,
  placeholder,
  validate = () => true 
}: ListInputProps<T>): ReactElement {
  const [input, setInput] = useState('');

  const handleAdd = () => {
    const trimmedInput = input.trim();
    if (trimmedInput && validate(trimmedInput)) {
      const newItem = createItem(trimmedInput);
      onChange([...value, newItem]);
      setInput('');
    }
  };

  const handleKeyDown = (event: React.KeyboardEvent<HTMLInputElement>) => {
    if (event.key === 'Enter') {
      event.preventDefault();
      handleAdd();
    }
  };

  const handleRemove = (itemToRemove: T) => {
    onChange(value.filter(item => getItemLabel(item) !== getItemLabel(itemToRemove)));
  };

  return (
    <Box>
      <Group gap="xs">
        <TextInput
          style={{ flex: 1 }}
          placeholder={placeholder}
          value={input}
          onChange={(e) => setInput(e.currentTarget.value)}
          onKeyDown={handleKeyDown}
        />
        <ActionIcon 
          variant="light" 
          color="blue" 
          onClick={handleAdd}
          disabled={!input.trim() || !validate(input.trim())}
        >
          <IconPlus size={16} />
        </ActionIcon>
      </Group>
      <Group gap="xs" mt="sm">
        {value.map((item) => (
          <Pill 
            key={getItemLabel(item)}
            withRemoveButton
            onRemove={() => handleRemove(item)}
          >
            {getItemLabel(item)}
          </Pill>
        ))}
      </Group>
    </Box>
  );
} 
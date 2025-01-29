import { ReactElement } from 'react';
import { ListInput } from './common/ListInput';
import { Tag } from '../types';

interface TagInputProps {
  value: Tag[];
  onChange: (tags: Tag[]) => void;
}

export function TagInput({ value, onChange }: TagInputProps): ReactElement {
  return (
    <ListInput<Tag>
      value={value}
      onChange={onChange}
      createItem={(name) => ({ name })}
      getItemLabel={(tag) => tag.name}
      placeholder="Type tag and press Enter"
    />
  );
} 
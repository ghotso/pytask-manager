import { ReactElement } from 'react';
import { Tag } from '../types';

interface TagInputProps {
  value: Tag[];
  onChange: (tags: Tag[]) => void;
}

export declare function TagInput(props: TagInputProps): ReactElement; 
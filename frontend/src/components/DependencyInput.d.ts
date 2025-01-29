import { ReactElement } from 'react';
import { Dependency } from '../types';

interface DependencyInputProps {
  value: Dependency[];
  onChange: (dependencies: Dependency[]) => void;
}

export declare function DependencyInput(props: DependencyInputProps): ReactElement; 
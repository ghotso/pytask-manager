import { ReactElement } from 'react';
import { TextInput } from '@mantine/core';
import { Dependency } from '../types';

interface DependencyInputProps {
  value: Dependency[];
  onChange: (dependencies: Dependency[]) => void;
}

export function DependencyInput({ value, onChange }: DependencyInputProps): ReactElement {
  const handleKeyDown = (event: React.KeyboardEvent<HTMLInputElement>) => {
    if (event.key === 'Enter') {
      event.preventDefault();
      const input = event.currentTarget;
      const text = input.value.trim();
      
      if (text) {
        // Parse package name and version spec
        let packageName = text;
        let versionSpec = '*';  // Default to latest version
        
        // Check for version specification (both package@version and package>=version formats)
        const atVersionMatch = text.match(/^([^@]+)@(.+)$/);
        const comparisonVersionMatch = text.match(/^([^><=]+)(>=|<=|==|>|<)(.+)$/);
        
        if (atVersionMatch) {
          packageName = atVersionMatch[1].trim();
          versionSpec = atVersionMatch[2];
        } else if (comparisonVersionMatch) {
          packageName = comparisonVersionMatch[1].trim();
          versionSpec = comparisonVersionMatch[2] + comparisonVersionMatch[3];
        }
        
        // Check if package already exists
        if (!value.some(dep => dep.package_name === packageName)) {
          onChange([
            ...value,
            {
              package_name: packageName,
              version_spec: versionSpec,
            },
          ]);
        }
        
        input.value = '';
      }
    }
  };

  return (
    <TextInput
      placeholder="Enter package name and version (e.g. requests>=2.0.0 or requests@2.0.0, or just package name for latest)"
      onKeyDown={handleKeyDown}
    />
  );
} 
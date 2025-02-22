import { ReactElement } from 'react';
import { Stack, Table, Text } from '@mantine/core';
import { ListInput } from './common/ListInput';
import { Dependency } from '../types';

interface DependencyInputProps {
  value: Dependency[];
  onChange: (dependencies: Dependency[]) => void;
}

export function DependencyInput({ value, onChange }: DependencyInputProps): ReactElement {
  const validateDependency = (input: string): boolean => {
    // Check for valid package name and version format
    const atVersionMatch = input.match(/^([^@]+)@(.+)$/);
    const comparisonVersionMatch = input.match(/^([^><=]+)(>=|<=|==|>|<)(.+)$/);
    const simplePackageMatch = input.match(/^[a-zA-Z0-9_-]+$/);

    return !!(atVersionMatch || comparisonVersionMatch || simplePackageMatch);
  };

  const createDependency = (input: string): Dependency => {
    let packageName = input;
    let versionSpec = '*';  // Default to latest version
    
    // Check for version specification (both package@version and package>=version formats)
    const atVersionMatch = input.match(/^([^@]+)@(.+)$/);
    const comparisonVersionMatch = input.match(/^([^><=]+)(>=|<=|==|>|<)(.+)$/);
    
    if (atVersionMatch) {
      packageName = atVersionMatch[1].trim();
      versionSpec = atVersionMatch[2];
    } else if (comparisonVersionMatch) {
      packageName = comparisonVersionMatch[1].trim();
      versionSpec = comparisonVersionMatch[2] + comparisonVersionMatch[3];
    }

    return {
      package_name: packageName,
      version_spec: versionSpec,
    };
  };

  return (
    <Stack gap="md">
      <ListInput<Dependency>
        value={value}
        onChange={onChange}
        createItem={createDependency}
        getItemLabel={(dep) => `${dep.package_name}${dep.version_spec === '*' ? '' : '@' + dep.version_spec}`}
        placeholder="Enter package name and version (e.g. requests>=2.0.0 or requests@2.0.0)"
        validate={validateDependency}
      />

      {value.length > 0 && (
        <Table>
          <Table.Thead>
            <Table.Tr>
              <Table.Th>Package Name</Table.Th>
              <Table.Th>Version</Table.Th>
              <Table.Th>Status</Table.Th>
            </Table.Tr>
          </Table.Thead>
          <Table.Tbody>
            {value.map((dep) => (
              <Table.Tr key={dep.package_name}>
                <Table.Td>
                  <Text>{dep.package_name}</Text>
                </Table.Td>
                <Table.Td>
                  <Text>{dep.version_spec || 'latest'}</Text>
                </Table.Td>
                <Table.Td>
                  <Text c={dep.installed_version ? 'green' : 'yellow'}>
                    {dep.installed_version ? `Installed (${dep.installed_version})` : 'Not Installed'}
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
import { ReactElement } from 'react';
import { Stack, Table, Badge, Button, TextInput, Group } from '@mantine/core';
import { IconTrash } from '@tabler/icons-react';
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

  const createDependency = (input: string): Dependency | null => {
    if (!validateDependency(input)) return null;

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

  const handleAddDependency = (input: string) => {
    const newDep = createDependency(input);
    if (newDep && !value.some(dep => dep.package_name === newDep.package_name)) {
      onChange([...value, newDep]);
    }
  };

  const handleRemoveDependency = (packageName: string) => {
    onChange(value.filter(dep => dep.package_name !== packageName));
  };

  return (
    <Stack gap="md">
      <Group>
        <TextInput
          placeholder="Enter package name and version (e.g. requests>=2.0.0 or requests@2.0.0)"
          style={{ flex: 1 }}
          onKeyDown={(e) => {
            if (e.key === 'Enter') {
              handleAddDependency(e.currentTarget.value);
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
          <col style={{ width: '35%' }} />
          <col style={{ width: '25%' }} />
          <col style={{ width: '30%' }} />
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
            }}>Package</th>
            <th style={{ 
              padding: '12px 16px',
              color: '#C1C2C5',
              fontWeight: 600,
              fontSize: '0.9rem',
              textAlign: 'left',
              borderBottom: '1px solid #2C2E33',
              backgroundColor: '#141517'
            }}>Version</th>
            <th style={{ 
              padding: '12px 16px',
              color: '#C1C2C5',
              fontWeight: 600,
              fontSize: '0.9rem',
              textAlign: 'left',
              borderBottom: '1px solid #2C2E33',
              backgroundColor: '#141517'
            }}>Status</th>
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
          {value.map((dep) => (
            <tr key={`${dep.package_name}-${dep.version_spec}`} style={{ backgroundColor: '#1A1B1E' }}>
              <td style={{ 
                padding: '12px 16px',
                color: '#C1C2C5',
                borderBottom: '1px solid #2C2E33',
                overflow: 'hidden',
                textOverflow: 'ellipsis',
                whiteSpace: 'nowrap'
              }}>
                {dep.package_name}
              </td>
              <td style={{ 
                padding: '12px 16px',
                color: '#C1C2C5',
                borderBottom: '1px solid #2C2E33',
                overflow: 'hidden',
                textOverflow: 'ellipsis',
                whiteSpace: 'nowrap'
              }}>
                {dep.version_spec || 'latest'}
              </td>
              <td style={{ 
                padding: '12px 16px',
                borderBottom: '1px solid #2C2E33',
                textAlign: 'left'
              }}>
                <Badge
                  color={dep.installed_version ? 'green' : 'yellow'}
                  variant="filled"
                  size="sm"
                  style={{ 
                    minWidth: '100px', 
                    textAlign: 'center',
                    display: 'inline-block'
                  }}
                >
                  {dep.installed_version ? `Installed (${dep.installed_version})` : 'Not Installed'}
                </Badge>
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
                  onClick={() => handleRemoveDependency(dep.package_name)}
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
                colSpan={4} 
                style={{ 
                  padding: '12px 16px',
                  color: '#666',
                  textAlign: 'center',
                  borderBottom: '1px solid #2C2E33'
                }}
              >
                No dependencies defined
              </td>
            </tr>
          )}
        </tbody>
      </Table>
    </Stack>
  );
} 
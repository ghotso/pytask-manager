import { NavLink, Group, Title, Stack, Button } from '@mantine/core';
import { Link, useLocation } from 'react-router-dom';
import { 
  IconList, 
  IconPlus, 
  IconHistory, 
  IconBrandPython 
} from '@tabler/icons-react';

export function Sidebar() {
  const location = useLocation();

  return (
    <Stack gap="xl">
      <Group mb={20}>
        <IconBrandPython size={30} style={{ color: '#3B82F6' }} />
        <Link to="/" style={{ textDecoration: 'none', color: 'inherit' }}>
          <Title order={1} size="h3">PyTask Manager</Title>
        </Link>
      </Group>

      <Stack gap="xs">
        <Button
          component={Link}
          to="/scripts/new"
          leftSection={<IconPlus size={16} />}
          fullWidth
          variant="filled"
          color="blue"
        >
          New Script
        </Button>

        <NavLink
          component={Link}
          to="/"
          label="Scripts"
          leftSection={<IconList size={16} />}
          active={location.pathname === '/' || location.pathname === '/scripts'}
          variant="filled"
          styles={{
            root: {
              borderRadius: '8px',
              '&[data-active]': {
                backgroundColor: '#1A1B1E',
              }
            }
          }}
        />

        <NavLink
          component={Link}
          to="/executions"
          label="Execution Logs"
          leftSection={<IconHistory size={16} />}
          active={location.pathname === '/executions'}
          variant="filled"
          styles={{
            root: {
              borderRadius: '8px',
              '&[data-active]': {
                backgroundColor: '#1A1B1E',
              }
            }
          }}
        />
      </Stack>
    </Stack>
  );
} 
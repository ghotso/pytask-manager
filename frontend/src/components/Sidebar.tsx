import { NavLink, Group, Title, Stack, Button, Box, Text } from '@mantine/core';
import { Link, useLocation } from 'react-router-dom';
import { 
  IconPlus, 
  IconHistory, 
  IconBrandPython,
  IconCode,
  IconDashboard,
} from '@tabler/icons-react';

export function Sidebar() {
  const location = useLocation();

  return (
    <Stack gap={0} h="100%">
      {/* Header */}
      <Box 
        p="md" 
        style={{ 
          borderBottom: '1px solid #2C2E33',
          background: 'linear-gradient(180deg, #1A1B1E 0%, #141517 100%)'
        }}
      >
        <Group mb={5}>
          <IconBrandPython 
            size={32} 
            style={{ 
              color: '#3B82F6',
              filter: 'drop-shadow(0 0 8px rgba(59, 130, 246, 0.5))'
            }} 
          />
          <Link to="/" style={{ textDecoration: 'none', color: 'inherit' }}>
            <Stack gap={0}>
              <Title order={1} size="h3">PyTask Manager</Title>
              <Text size="xs" c="dimmed">Script Management System</Text>
            </Stack>
          </Link>
        </Group>
      </Box>

      {/* Main Navigation */}
      <Box p="md" style={{ flex: 1 }}>
        <Stack gap="xs">
          <Button
            component={Link}
            to="/scripts/new"
            leftSection={<IconPlus size={18} />}
            fullWidth
            variant="gradient"
            gradient={{ from: '#3B82F6', to: '#2563EB', deg: 45 }}
            styles={{
              root: {
                height: 45,
                transition: 'transform 0.2s ease',
                '&:hover': {
                  transform: 'translateY(-2px)',
                }
              }
            }}
          >
            New Script
          </Button>

          <Box mt="md">
            <Text size="xs" fw={700} c="dimmed" mb="xs" pl="sm">
              NAVIGATION
            </Text>
            
            <Stack gap={8}>
              <NavLink
                component={Link}
                to="/"
                label="Dashboard"
                leftSection={<IconDashboard size={18} />}
                active={location.pathname === '/'}
                styles={{
                  root: {
                    borderRadius: '8px',
                    padding: '12px 16px',
                    color: '#C1C2C5',
                    transition: 'all 0.2s ease',
                    '&[data-active]': {
                      backgroundColor: '#25262B',
                      color: '#fff',
                      boxShadow: '0 2px 4px rgba(0,0,0,0.2)',
                    },
                    '&:hover': {
                      backgroundColor: '#25262B',
                      transform: 'translateX(4px)',
                    }
                  }
                }}
              />

              <NavLink
                component={Link}
                to="/scripts"
                label="Scripts"
                leftSection={<IconCode size={18} />}
                active={location.pathname === '/scripts'}
                styles={{
                  root: {
                    borderRadius: '8px',
                    padding: '12px 16px',
                    color: '#C1C2C5',
                    transition: 'all 0.2s ease',
                    '&[data-active]': {
                      backgroundColor: '#25262B',
                      color: '#fff',
                      boxShadow: '0 2px 4px rgba(0,0,0,0.2)',
                    },
                    '&:hover': {
                      backgroundColor: '#25262B',
                      transform: 'translateX(4px)',
                    }
                  }
                }}
              />

              <NavLink
                component={Link}
                to="/executions"
                label="Execution Logs"
                leftSection={<IconHistory size={18} />}
                active={location.pathname === '/executions'}
                styles={{
                  root: {
                    borderRadius: '8px',
                    padding: '12px 16px',
                    color: '#C1C2C5',
                    transition: 'all 0.2s ease',
                    '&[data-active]': {
                      backgroundColor: '#25262B',
                      color: '#fff',
                      boxShadow: '0 2px 4px rgba(0,0,0,0.2)',
                    },
                    '&:hover': {
                      backgroundColor: '#25262B',
                      transform: 'translateX(4px)',
                    }
                  }
                }}
              />
            </Stack>
          </Box>
        </Stack>
      </Box>
    </Stack>
  );
} 
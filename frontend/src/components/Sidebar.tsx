import { NavLink, Group, Title, Stack, Button, Box, Text, rem } from '@mantine/core';
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
    <Stack gap={0} h="100%" style={{ overflow: 'hidden' }}>
      {/* Header */}
      <Box 
        p="md" 
        style={{ 
          borderBottom: '1px solid rgba(44, 46, 51, 0.5)',
          background: 'linear-gradient(180deg, rgba(26, 27, 30, 0.9) 0%, rgba(20, 21, 23, 0.8) 100%)',
          backdropFilter: 'blur(10px)',
        }}
      >
        <Group mb={5}>
          <IconBrandPython 
            size={36} 
            style={{ 
              color: '#3B82F6',
              filter: 'drop-shadow(0 0 12px rgba(59, 130, 246, 0.6))'
            }} 
          />
          <Link to="/" style={{ textDecoration: 'none', color: 'inherit' }}>
            <Stack gap={2}>
              <Title order={1} size="h3">PyTask Manager</Title>
              <Text size="xs" c="dimmed" style={{ letterSpacing: '0.3px' }}>Script Management System</Text>
            </Stack>
          </Link>
        </Group>
      </Box>

      {/* Main Navigation */}
      <Box p="md" style={{ flex: 1 }}>
        <Stack gap="lg">
          <Button
            component={Link}
            to="/scripts/new"
            leftSection={<IconPlus size={18} />}
            fullWidth
            h={rem(45)}
            variant="gradient"
            gradient={{ from: '#3B82F6', to: '#2563EB', deg: 45 }}
            styles={{
              root: {
                border: '1px solid rgba(59, 130, 246, 0.2)',
                boxShadow: '0 4px 12px rgba(59, 130, 246, 0.2)',
                transition: 'all 0.2s ease',
                '&:hover': {
                  transform: 'translateY(-2px)',
                  boxShadow: '0 6px 16px rgba(59, 130, 246, 0.3)',
                }
              }
            }}
          >
            New Script
          </Button>

          <Box>
            <Text size="xs" fw={700} c="dimmed" mb="xs" pl="sm" style={{ letterSpacing: '0.5px' }}>
              NAVIGATION
            </Text>
            
            <Stack gap={8}>
              <NavLink
                component={Link}
                to="/"
                label="Dashboard"
                leftSection={
                  <IconDashboard 
                    size={20} 
                    style={{ 
                      color: location.pathname === '/' ? '#3B82F6' : 'currentColor',
                      transition: 'color 0.2s ease'
                    }} 
                  />
                }
                active={location.pathname === '/'}
                styles={{
                  root: {
                    borderRadius: '10px',
                    padding: '12px 16px',
                    color: '#C1C2C5',
                    transition: 'all 0.2s ease',
                    '&[data-active]': {
                      backgroundColor: 'rgba(59, 130, 246, 0.15)',
                      color: '#fff',
                      boxShadow: '0 2px 8px rgba(0, 0, 0, 0.2)',
                    },
                    '&:hover': {
                      backgroundColor: 'rgba(59, 130, 246, 0.1)',
                      transform: 'translateX(4px)',
                    }
                  }
                }}
              />

              <NavLink
                component={Link}
                to="/scripts"
                label="Scripts"
                leftSection={
                  <IconCode 
                    size={20} 
                    style={{ 
                      color: location.pathname === '/scripts' ? '#3B82F6' : 'currentColor',
                      transition: 'color 0.2s ease'
                    }} 
                  />
                }
                active={location.pathname === '/scripts'}
                styles={{
                  root: {
                    borderRadius: '10px',
                    padding: '12px 16px',
                    color: '#C1C2C5',
                    transition: 'all 0.2s ease',
                    '&[data-active]': {
                      backgroundColor: 'rgba(59, 130, 246, 0.15)',
                      color: '#fff',
                      boxShadow: '0 2px 8px rgba(0, 0, 0, 0.2)',
                    },
                    '&:hover': {
                      backgroundColor: 'rgba(59, 130, 246, 0.1)',
                      transform: 'translateX(4px)',
                    }
                  }
                }}
              />

              <NavLink
                component={Link}
                to="/executions"
                label="Execution Logs"
                leftSection={
                  <IconHistory 
                    size={20} 
                    style={{ 
                      color: location.pathname === '/executions' ? '#3B82F6' : 'currentColor',
                      transition: 'color 0.2s ease'
                    }} 
                  />
                }
                active={location.pathname === '/executions'}
                styles={{
                  root: {
                    borderRadius: '10px',
                    padding: '12px 16px',
                    color: '#C1C2C5',
                    transition: 'all 0.2s ease',
                    '&[data-active]': {
                      backgroundColor: 'rgba(59, 130, 246, 0.15)',
                      color: '#fff',
                      boxShadow: '0 2px 8px rgba(0, 0, 0, 0.2)',
                    },
                    '&:hover': {
                      backgroundColor: 'rgba(59, 130, 246, 0.1)',
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
import {
  AppShell,
  Burger,
  Group,
  Title,
} from '@mantine/core';
import { useDisclosure } from '@mantine/hooks';
import { IconBrandPython } from '@tabler/icons-react';
import { ReactNode } from 'react';
import { Link } from 'react-router-dom';
import { Sidebar } from './Sidebar';

interface LayoutProps {
  children: ReactNode;
}

export function Layout({ children }: LayoutProps) {
  const [opened, { toggle }] = useDisclosure();

  return (
    <AppShell
      header={{ height: 60 }}
      navbar={{ 
        width: 250,
        breakpoint: 'sm',
        collapsed: { mobile: !opened }
      }}
      padding={0}
      styles={{
        main: {
          background: '#0A0C12',
          paddingLeft: 250,
          width: '100vw',
          maxWidth: '100vw',
        },
        header: {
          background: '#0A0C12',
          borderBottom: '1px solid #1A1B1E',
        },
        navbar: {
          background: '#0A0C12',
          borderRight: '1px solid #1A1B1E',
          position: 'fixed',
          left: 0,
          top: 60,
          bottom: 0,
        }
      }}
    >
      <AppShell.Header>
        <Group h="100%" px="md">
          <Burger opened={opened} onClick={toggle} hiddenFrom="sm" size="sm" />
          <Group>
            <IconBrandPython size={30} style={{ color: '#3B82F6' }} />
            <Link to="/" style={{ textDecoration: 'none', color: 'inherit' }}>
              <Title order={1} size="h3">PyTask Manager</Title>
            </Link>
          </Group>
        </Group>
      </AppShell.Header>

      <AppShell.Navbar p="md">
        <Sidebar />
      </AppShell.Navbar>

      <AppShell.Main>
        {children}
      </AppShell.Main>
    </AppShell>
  );
} 
import {
  AppShell,
  Burger,
} from '@mantine/core';
import { useDisclosure } from '@mantine/hooks';
import { ReactNode } from 'react';
import { Sidebar } from './Sidebar';

interface LayoutProps {
  children: ReactNode;
}

export function Layout({ children }: LayoutProps) {
  const [opened, { toggle }] = useDisclosure();

  return (
    <AppShell
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
        navbar: {
          background: '#0A0C12',
          borderRight: '1px solid #1A1B1E',
          position: 'fixed',
          left: 0,
          top: 0,
          bottom: 0,
        }
      }}
    >
      <AppShell.Navbar p="md">
        <Burger opened={opened} onClick={toggle} hiddenFrom="sm" size="sm" mb="xl" />
        <Sidebar />
      </AppShell.Navbar>

      <AppShell.Main>
        {children}
      </AppShell.Main>
    </AppShell>
  );
} 
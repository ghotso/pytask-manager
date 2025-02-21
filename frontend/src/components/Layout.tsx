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
        width: 280,
        breakpoint: 'sm',
        collapsed: { mobile: !opened }
      }}
      padding={0}
      styles={{
        main: {
          background: '#0A0C12',
          paddingLeft: 280,
          width: '100vw',
          maxWidth: '100vw',
        },
        navbar: {
          background: 'linear-gradient(180deg, #0A0C12 0%, #141517 100%)',
          borderRight: '1px solid rgba(26, 27, 30, 0.5)',
          position: 'fixed',
          left: 0,
          top: 0,
          bottom: 0,
          boxShadow: '2px 0 20px rgba(0, 0, 0, 0.3)',
        }
      }}
    >
      <AppShell.Navbar p={0}>
        <Burger opened={opened} onClick={toggle} hiddenFrom="sm" size="sm" m="md" />
        <Sidebar />
      </AppShell.Navbar>

      <AppShell.Main>
        {children}
      </AppShell.Main>
    </AppShell>
  );
} 
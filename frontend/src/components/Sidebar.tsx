import { NavLink } from '@mantine/core';
import { Link, useLocation } from 'react-router-dom';
import { IconList, IconPlus, IconHistory } from '@tabler/icons-react';

export function Sidebar() {
  const location = useLocation();

  return (
    <div style={{ padding: '20px' }}>
      <NavLink
        component={Link}
        to="/"
        label="Scripts"
        leftSection={<IconList size={16} />}
        active={location.pathname === '/' || location.pathname === '/scripts'}
      />
      <NavLink
        component={Link}
        to="/scripts/new"
        label="New Script"
        leftSection={<IconPlus size={16} />}
        active={location.pathname === '/scripts/new'}
      />
      <NavLink
        component={Link}
        to="/executions"
        label="Execution Logs"
        leftSection={<IconHistory size={16} />}
        active={location.pathname === '/executions'}
      />
    </div>
  );
} 
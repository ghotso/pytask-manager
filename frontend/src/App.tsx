import '@mantine/core/styles.css';
import '@mantine/notifications/styles.css';

import { MantineProvider, createTheme } from '@mantine/core';
import { Notifications } from '@mantine/notifications';
import { BrowserRouter, Route, Routes } from 'react-router-dom';
import { Layout } from './components/Layout';
import { ScriptExecution } from './components/ScriptExecution';
import { ScriptForm } from './components/ScriptForm';
import { ScriptList } from './components/ScriptList';
import { ScriptSchedules } from './components/ScriptSchedules';
import { ScriptDetailPage } from './pages/ScriptDetailPage';
import { ExecutionLogsPage } from './pages/ExecutionLogsPage';

const theme = createTheme({
  primaryColor: 'blue',
  defaultRadius: 'sm',
  colors: {
    dark: [
      '#C1C2C5',
      '#A6A7AB',
      '#909296',
      '#5C5F66',
      '#373A40',
      '#2C2E33',
      '#25262B',
      '#1A1B1E',
      '#141517',
      '#101113',
    ],
  },
  components: {
    AppShell: {
      styles: {
        main: {
          background: '#0A0C12',
        },
      },
    },
  },
});

export default function App() {
  return (
    <MantineProvider theme={theme} defaultColorScheme="dark">
      <Notifications />
      <BrowserRouter>
        <Layout>
          <Routes>
            <Route path="/" element={<ScriptList />} />
            <Route path="/scripts/new" element={<ScriptForm />} />
            <Route path="/scripts/:id" element={<ScriptDetailPage />} />
            <Route
              path="/scripts/:id/execute"
              element={<ScriptExecution />}
            />
            <Route
              path="/scripts/:id/schedules"
              element={<ScriptSchedules />}
            />
            <Route path="/executions" element={<ExecutionLogsPage />} />
          </Routes>
        </Layout>
      </BrowserRouter>
    </MantineProvider>
  );
}

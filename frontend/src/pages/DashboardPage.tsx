import { useEffect, useState } from 'react';
import { 
  Box, 
  Card, 
  Group, 
  Text, 
  Title, 
  Stack,
  SimpleGrid,
  Button,
  Badge,
  Container,
} from '@mantine/core';
import { Link, useNavigate } from 'react-router-dom';
import { 
  IconCheck,
  IconX,
  IconLoader2,
  IconClock,
  IconScript,
  IconAlertTriangle,
  IconPlayerPause,
  IconCalendarTime,
} from '@tabler/icons-react';
import { Script, Execution, ExecutionStatus } from '../types';
import { scriptsApi } from '../api/client';
import { formatDate } from '../utils/date';

interface DashboardStats {
  activeScripts: number;
  inactiveScripts: number;
  scriptsWithUninstalledDeps: number;
  scriptsWithFailedLastRun: number;
  nextScheduledScript: {
    name: string;
    scheduledTime: string;
  } | null;
}

interface NextExecution {
  name: string;
  time: Date;
}

export function DashboardPage() {
  const navigate = useNavigate();
  const [stats, setStats] = useState<DashboardStats>({
    activeScripts: 0,
    inactiveScripts: 0,
    scriptsWithUninstalledDeps: 0,
    scriptsWithFailedLastRun: 0,
    nextScheduledScript: null,
  });
  const [recentExecutions, setRecentExecutions] = useState<(Execution & { scriptName: string })[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    loadDashboardData();
    // Refresh data every 30 seconds
    const interval = setInterval(loadDashboardData, 30000);
    return () => clearInterval(interval);
  }, []);

  const loadDashboardData = async () => {
    try {
      setIsLoading(true);
      const scripts = await scriptsApi.list();
      
      // Calculate statistics
      const activeScripts = scripts.filter(s => s.is_active).length;
      const inactiveScripts = scripts.length - activeScripts;
      const scriptsWithUninstalledDeps = scripts.filter(s => 
        s.dependencies.some(d => !d.installed_version)
      ).length;

      // Get last execution for each script and count failures
      let failedScripts = 0;
      for (const script of scripts) {
        try {
          const executions = await scriptsApi.listExecutions(script.id, 1); // Get only the most recent execution
          if (executions.length > 0 && executions[0].status === ExecutionStatus.FAILURE) {
            failedScripts++;
          }
        } catch (error) {
          console.error(`Failed to get executions for script ${script.id}:`, error);
        }
      }

      // Find next scheduled script
      const nextScript = findNextScheduledScript(scripts);

      setStats({
        activeScripts,
        inactiveScripts,
        scriptsWithUninstalledDeps,
        scriptsWithFailedLastRun: failedScripts,
        nextScheduledScript: nextScript,
      });

      // Load recent executions
      const allExecutions: (Execution & { scriptName: string })[] = [];
      for (const script of scripts) {
        const executions = await scriptsApi.listExecutions(script.id, 8); // Limit to 8 executions per script
        allExecutions.push(
          ...executions.map(exec => ({
            ...exec,
            scriptName: script.name,
          }))
        );
      }

      // Sort by start time and take the 8 most recent
      const sortedExecutions = allExecutions
        .sort((a, b) => new Date(b.started_at).getTime() - new Date(a.started_at).getTime())
        .slice(0, 8);

      setRecentExecutions(sortedExecutions);
    } catch (error) {
      console.error('Failed to load dashboard data:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const findNextScheduledScript = (scripts: Script[]) => {
    const now = new Date();
    let nextExecution: NextExecution | null = null;

    for (const script of scripts) {
      if (!script.is_active || !script.schedules.length) continue;

      // This is a placeholder - in reality, you'd need to calculate the next execution
      // time based on the cron expression. For now, we'll just use a dummy future time
      const dummyNextTime = new Date(now.getTime() + 3600000); // 1 hour from now
      
      if (!nextExecution || dummyNextTime < nextExecution.time) {
        nextExecution = {
          name: script.name,
          time: dummyNextTime,
        };
      }
    }

    return nextExecution ? {
      name: nextExecution.name,
      scheduledTime: formatDate(nextExecution.time.toISOString()),
    } : null;
  };

  return (
    <Box p="xl">
      <Container size="xl">
        <Stack gap="xl">
          <Title>Dashboard</Title>

          {/* Statistics Cards */}
          {isLoading ? (
            <Text c="dimmed" ta="center">Loading dashboard data...</Text>
          ) : (
          <SimpleGrid cols={4}>
            <Card 
              withBorder 
              component={Link} 
              to="/scripts?filter=active"
              style={{ 
                textDecoration: 'none', 
                color: 'inherit',
                cursor: 'pointer',
                transition: 'transform 0.2s ease',
                '&:hover': {
                  transform: 'translateY(-2px)',
                }
              }}
            >
              <Group>
                <IconScript size={24} color="var(--mantine-color-blue-filled)" />
                <div>
                  <Text size="xl" fw={700}>{stats.activeScripts}</Text>
                  <Text size="sm" c="dimmed">Active Scripts</Text>
                </div>
              </Group>
            </Card>

            <Card 
              withBorder 
              component={Link} 
              to="/scripts?filter=inactive"
              style={{ 
                textDecoration: 'none', 
                color: 'inherit',
                cursor: 'pointer',
                transition: 'transform 0.2s ease',
                '&:hover': {
                  transform: 'translateY(-2px)',
                }
              }}
            >
              <Group>
                <IconPlayerPause size={24} color="var(--mantine-color-yellow-filled)" />
                <div>
                  <Text size="xl" fw={700}>{stats.inactiveScripts}</Text>
                  <Text size="sm" c="dimmed">Inactive Scripts</Text>
                </div>
              </Group>
            </Card>

            <Card 
              withBorder 
              component={Link} 
              to="/scripts?filter=missing-deps"
              style={{ 
                textDecoration: 'none', 
                color: 'inherit',
                cursor: 'pointer',
                transition: 'transform 0.2s ease',
                '&:hover': {
                  transform: 'translateY(-2px)',
                }
              }}
            >
              <Group>
                <IconAlertTriangle size={24} color="var(--mantine-color-orange-filled)" />
                <div>
                  <Text size="xl" fw={700}>{stats.scriptsWithUninstalledDeps}</Text>
                  <Text size="sm" c="dimmed">Scripts with Missing Dependencies</Text>
                </div>
              </Group>
            </Card>

            <Card 
              withBorder 
              component={Link} 
              to="/scripts?filter=failed"
              style={{ 
                textDecoration: 'none', 
                color: 'inherit',
                cursor: 'pointer',
                transition: 'transform 0.2s ease',
                '&:hover': {
                  transform: 'translateY(-2px)',
                }
              }}
            >
              <Group>
                <IconX size={24} color="var(--mantine-color-red-filled)" />
                <div>
                  <Text size="xl" fw={700}>{stats.scriptsWithFailedLastRun}</Text>
                  <Text size="sm" c="dimmed">Scripts with Failed Last Run</Text>
                </div>
              </Group>
            </Card>
          </SimpleGrid>
          )}

          {/* Next Scheduled Script */}
          {stats.nextScheduledScript && (
            <Card withBorder>
              <Group>
                <IconCalendarTime size={24} color="var(--mantine-color-blue-filled)" />
                <div>
                  <Text fw={500}>Next Scheduled Execution</Text>
                  <Text size="sm">
                    {stats.nextScheduledScript.name} at {stats.nextScheduledScript.scheduledTime}
                  </Text>
                </div>
              </Group>
            </Card>
          )}

          {/* Recent Executions */}
          <Stack>
            <Group justify="space-between">
              <Title order={2}>Recent Executions</Title>
              <Button component={Link} to="/executions" variant="light">
                View All Executions
              </Button>
            </Group>

            <SimpleGrid cols={4}>
              {recentExecutions.map((execution) => (
                <Card 
                  key={execution.id} 
                  withBorder
                  style={{
                    cursor: 'pointer',
                    transition: 'transform 0.2s ease',
                    '&:hover': {
                      transform: 'translateY(-2px)',
                    }
                  }}
                  onClick={() => navigate(`/scripts/${execution.script_id}`)}
                >
                  <Stack gap="xs">
                    <Group justify="space-between">
                      <Text fw={500} lineClamp={1}>
                        {execution.scriptName}
                      </Text>
                      <Badge
                        color={
                          execution.status === ExecutionStatus.SUCCESS ? 'green' :
                          execution.status === ExecutionStatus.FAILURE ? 'red' :
                          execution.status === ExecutionStatus.RUNNING ? 'blue' :
                          'gray'
                        }
                        leftSection={
                          execution.status === ExecutionStatus.SUCCESS ? (
                            <IconCheck size={12} />
                          ) : execution.status === ExecutionStatus.FAILURE ? (
                            <IconX size={12} />
                          ) : execution.status === ExecutionStatus.RUNNING ? (
                            <IconLoader2 size={12} className="rotating" />
                          ) : (
                            <IconClock size={12} />
                          )
                        }
                      >
                        {execution.status}
                      </Badge>
                    </Group>
                    <Text size="sm" c="dimmed">
                      {formatDate(execution.started_at)}
                    </Text>
                  </Stack>
                </Card>
              ))}
            </SimpleGrid>
          </Stack>
        </Stack>
      </Container>
    </Box>
  );
} 
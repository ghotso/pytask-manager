import axios from 'axios';
import type { Script, Tag, Dependency, Schedule, Execution } from '../types';
import { API_BASE_URL, WS_BASE_URL } from '../config';

export type { Script, Tag, Dependency, Schedule, Execution };

export interface CreateScriptData {
  name: string;
  description?: string;
  content: string;
  is_active: boolean;
  tags: string[];
  dependencies: Array<{
    package_name: string;
    version_spec: string;
  }>;
  schedules: Array<{
    cron_expression: string;
    description?: string;
  }>;
}

export interface UpdateScriptData {
  name?: string;
  description?: string;
  content?: string;
  is_active?: boolean;
  tags?: string[];
  dependencies?: Array<{
    package_name: string;
    version_spec: string;
  }>;
  schedules?: Array<{
    cron_expression: string;
    description?: string;
  }>;
}

export interface CreateScheduleData {
  cron_expression: string;
  description?: string;
}

export interface UpdateScheduleData {
  cron_expression?: string;
  description?: string;
}

const api = axios.create({
  baseURL: API_BASE_URL,
});

export const scriptsApi = {
  list: async () => {
    const response = await api.get<Script[]>('/api/scripts');
    return response.data;
  },

  get: async (id: number) => {
    const response = await api.get<Script>(`/api/scripts/${id}`);
    return response.data;
  },

  create: async (data: CreateScriptData) => {
    const response = await api.post<Script>('/api/scripts', data);
    return response.data;
  },

  update: async (id: number, data: UpdateScriptData) => {
    const response = await api.put<Script>(`/api/scripts/${id}`, data);
    return response.data;
  },

  delete: async (id: number) => {
    await api.delete(`/api/scripts/${id}`);
  },

  execute: (id: number): WebSocket => {
    const wsUrl = `${WS_BASE_URL}/api/scripts/${id}/ws`;
    return new WebSocket(wsUrl);
  },

  checkDependencies: async (id: number) => {
    const response = await api.post<string[]>(`/api/scripts/${id}/check-dependencies`);
    return response.data;
  },

  updateDependencies: async (id: number) => {
    const response = await api.post<void>(`/api/scripts/${id}/update-dependencies`);
    return response.data;
  },

  listExecutions: async (id: number, limit = 100, offset = 0) => {
    const response = await api.get<Execution[]>(`/api/scripts/${id}/executions`, {
      params: { limit, offset },
    });
    return response.data;
  },

  getExecutionLogs: async (scriptId: number, executionId: number) => {
    console.log('Fetching logs for execution:', executionId);
    const response = await api.get<string>(
      `/api/scripts/${scriptId}/executions/${executionId}/logs`
    );
    console.log('Received logs:', response.data);
    return response.data;
  },

  installDependencies: async (scriptId: number) => {
    console.log('Installing dependencies for script:', scriptId);
    const response = await api.post<void>(
      `/api/scripts/${scriptId}/install-dependencies`
    );
    return response.data;
  },

  async uninstallDependency(scriptId: number, packageName: string): Promise<void> {
    await api.post(`/api/scripts/${scriptId}/dependencies/uninstall`, {
      package_name: packageName
    });
  }
};

export const schedulesApi = {
  create: async (scriptId: number, data: CreateScheduleData) => {
    const response = await api.post<Schedule>(`/scripts/${scriptId}/schedules`, data);
    return response.data;
  },

  update: async (scriptId: number, scheduleId: number, data: UpdateScheduleData) => {
    const response = await api.put<Schedule>(
      `/scripts/${scriptId}/schedules/${scheduleId}`,
      data,
    );
    return response.data;
  },

  delete: async (scriptId: number, scheduleId: number) => {
    await api.delete(`/scripts/${scriptId}/schedules/${scheduleId}`);
  },
}; 
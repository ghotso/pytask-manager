export interface Tag {
  id?: number;
  name: string;
}

export interface Dependency {
  id?: number;
  script_id?: number;
  package_name: string;
  version_spec: string;
  installed_version?: string;
}

export interface Schedule {
  id?: number;
  script_id?: number;
  cron_expression: string;
  description?: string;
  created_at?: string;
}

export interface Execution {
  id: number;
  script_id: number;
  status: ExecutionStatus;
  started_at: string;
  ended_at?: string;
  error_message?: string;
  log_output?: string;
}

export enum ExecutionStatus {
  PENDING = 'pending',
  RUNNING = 'running',
  SUCCESS = 'success',
  FAILURE = 'failure'
}

export interface Script {
  id: number;
  name: string;
  description: string;
  content: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
  tags: Tag[];
  dependencies: Dependency[];
  schedules: Schedule[];
} 
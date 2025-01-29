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

export interface Script {
  id: number;
  name: string;
  description: string | null;
  content: string;
  is_active: boolean;
  tags: Tag[];
  dependencies: Dependency[];
  schedules: Schedule[];
  created_at: string;
  updated_at: string;
}

export interface Execution {
  id: number;
  script_id: number;
  started_at: string;
  completed_at?: string;
  status: ExecutionStatus;
  log_output?: string;
  error_message?: string;
}

export interface Schedule {
  id?: number;
  script_id?: number;
  cron_expression: string;
  description?: string;
  created_at?: string;
  updated_at?: string;
}

export enum ExecutionStatus {
  SUCCESS = 'success',
  PENDING = 'pending',
  RUNNING = 'running',
  FAILED = 'failure'
} 
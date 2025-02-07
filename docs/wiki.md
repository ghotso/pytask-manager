# PyTask-Manager Wiki

## Table of Contents
- [Pages](#pages)
  - [Dashboard / Script List](#dashboard--script-list)
  - [Script Detail Page](#script-detail-page)
  - [Script Execution Page](#script-execution-page)
  - [Script Schedules Page](#script-schedules-page)
  - [Execution Logs Page](#execution-logs-page)
- [Components](#components)
  - [Code Editor](#code-editor)
  - [Dependency Management](#dependency-management)
  - [Tag Management](#tag-management)
  - [Schedule Management](#schedule-management)
  - [Execution Controls](#execution-controls)
- [Functions & Features](#functions--features)
  - [Script Management](#script-management)
  - [Dependency Management](#dependency-management-1)
  - [Execution Management](#execution-management)
  - [Schedule Management](#schedule-management-1)

## Pages

### Dashboard / Script List
**Location**: `/` (root path)
**Component**: `ScriptList.tsx`

The main dashboard displays all available Python scripts with their key information:
- Script name and description
- Active/Inactive status
- Tags
- Last execution status
- Quick actions (run, edit, delete)

**Key Features**:
- Filter scripts by tags
- Search scripts by name
- Toggle script active status
- Quick access to script execution and editing

### Script Detail Page
**Location**: `/scripts/:id`
**Component**: `ScriptDetailPage.tsx`

Detailed view and editing interface for a single script:
- Code editor with syntax highlighting
- Dependency management
- Tag management
- Script metadata (name, description)
- Execution history

**Key Features**:
- Real-time code editing with Monaco Editor
- Install/uninstall dependencies
- Add/remove tags
- View execution history
- Execute script directly

### Script Execution Page
**Location**: `/scripts/:id/execute`
**Component**: `ScriptExecution.tsx`

Dedicated page for script execution and monitoring:
- Real-time execution logs
- Execution status indicator
- Error messages (if any)
- Output streaming

**Key Features**:
- WebSocket-based real-time log streaming
- Execution status updates
- Error handling and display
- Execution history recording

### Script Schedules Page
**Location**: `/scripts/:id/schedules`
**Component**: `ScriptSchedules.tsx`

Interface for managing script execution schedules:
- List of existing schedules
- Schedule creation form
- Cron expression input
- Human-readable schedule descriptions

**Key Features**:
- Create new schedules with cron expressions
- Edit existing schedules
- Delete schedules
- View upcoming executions

### Execution Logs Page
**Location**: `/executions`
**Component**: `ExecutionLogsPage.tsx`

Comprehensive view of all script executions:
- Execution history across all scripts
- Filtering by script and status
- Detailed log viewing
- Error tracking

**Key Features**:
- Filter executions by script
- Filter by execution status
- View detailed logs
- Sort by date/time

## Components

### Code Editor
**Component**: `CodeEditor.tsx`

Advanced code editing component based on Monaco Editor:
- Python syntax highlighting
- Auto-completion
- Error detection
- Line numbers

**Key Features**:
- Syntax highlighting for Python
- Auto-adjusting height
- Dark theme support
- Code formatting

### Dependency Management
**Component**: `DependencyInput.tsx`

Interface for managing Python package dependencies:
- Add new dependencies
- Specify version requirements
- View installed versions
- Remove dependencies

**Key Features**:
- Package name validation
- Version specification support
- Real-time dependency installation
- Installation status monitoring

### Tag Management
**Component**: `TagInput.tsx`

Component for managing script tags:
- Add/remove tags
- Tag suggestions
- Tag filtering

**Key Features**:
- Tag creation
- Tag deletion
- Tag validation
- Auto-completion

### Schedule Management
**Component**: `ScheduleInput.tsx`

Interface for creating and managing execution schedules:
- Cron expression input
- Human-readable descriptions
- Schedule validation

**Key Features**:
- Cron expression validation
- Human-readable schedule preview
- Schedule editing
- Schedule removal

### Execution Controls
**Component**: `ScriptExecution.tsx`

Controls and monitoring for script execution:
- Start/Stop execution
- Real-time log viewing
- Status monitoring
- Error handling

**Key Features**:
- WebSocket connection management
- Log streaming
- Status updates
- Error reporting

## Functions & Features

### Script Management

#### Create Script
```typescript
async function createScript(data: CreateScriptData): Promise<Script>
```
Creates a new Python script with specified metadata, content, and configurations.

#### Update Script
```typescript
async function updateScript(id: number, data: UpdateScriptData): Promise<Script>
```
Updates an existing script's content, metadata, or configurations.

#### Delete Script
```typescript
async function deleteScript(id: number): Promise<void>
```
Removes a script and all associated data (dependencies, schedules, executions).

### Dependency Management

#### Install Dependencies
```typescript
async function installDependencies(scriptId: number): Promise<void>
```
Installs all dependencies for a script in its virtual environment.

#### Uninstall Dependency
```typescript
async function uninstallDependency(scriptId: number, packageName: string): Promise<void>
```
Removes a specific dependency from a script's virtual environment.

#### Check Dependencies
```typescript
async function checkDependencies(scriptId: number): Promise<string[]>
```
Verifies the installation status of all dependencies.

### Execution Management

#### Execute Script
```typescript
async function executeScript(scriptId: number): Promise<Execution>
```
Starts a script execution and returns execution details.

#### Stream Logs
```typescript
function setupWebSocket(scriptId: number): WebSocket
```
Establishes WebSocket connection for real-time log streaming.

#### Get Execution Logs
```typescript
async function getExecutionLogs(scriptId: number, executionId: number): Promise<string>
```
Retrieves complete logs for a specific execution.

### Schedule Management

#### Create Schedule
```typescript
async function createSchedule(scriptId: number, data: CreateScheduleData): Promise<Schedule>
```
Creates a new execution schedule for a script.

#### Update Schedule
```typescript
async function updateSchedule(scriptId: number, scheduleId: number, data: UpdateScheduleData): Promise<Schedule>
```
Modifies an existing execution schedule.

#### Delete Schedule
```typescript
async function deleteSchedule(scriptId: number, scheduleId: number): Promise<void>
```
Removes an execution schedule.

## WebSocket Events

### Script Execution
- `execution_started`: Indicates the start of script execution
- `log_output`: Contains new log lines from the script
- `execution_finished`: Indicates completion of script execution
- `execution_error`: Contains error information if execution fails

### Dependency Installation
- `installation_started`: Indicates the start of dependency installation
- `installation_progress`: Contains installation progress information
- `installation_finished`: Indicates completion of installation
- `installation_error`: Contains error information if installation fails

## Error Handling

The application implements comprehensive error handling:
- API request errors with detailed messages
- WebSocket connection failures
- Script execution errors
- Dependency installation failures
- Schedule validation errors

Each error is logged and displayed to the user through the UI, with appropriate recovery options where possible.

## Security Features

- Script isolation using virtual environments
- Input validation and sanitization
- Secure WebSocket connections
- Resource usage limits
- Error logging and monitoring

## Best Practices

1. **Script Management**
   - Use descriptive names for scripts
   - Add meaningful tags for organization
   - Include detailed descriptions
   - Keep dependencies up to date

2. **Execution**
   - Monitor resource usage
   - Review execution logs
   - Handle errors appropriately
   - Use schedules responsibly

3. **Development**
   - Follow code style guidelines
   - Write clear documentation
   - Test changes thoroughly
   - Review security implications 
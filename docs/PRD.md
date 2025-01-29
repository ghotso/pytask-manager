**Product Requirements Document (PRD): PyTask-Manager**

---

## **Product Overview**

The **PyTask-Manager** is a self-hosted web application designed to enable users to create, manage, and execute Python scripts in an isolated and secure environment. The application provides tools for managing custom dependencies for each script and supports both manual and scheduled execution. It is intended for local use only and does not require user authentication.

---

## **Objectives**

- Provide an intuitive web interface for creating, editing, and managing Python scripts.
- Allow per-script dependency management, including pip packages.
- Enable manual execution of scripts with real-time feedback.
- Support scheduled execution using cron-based schedules.
- Store execution logs for auditing and debugging.
- Ensure the application is easily deployable as a Docker container.

Each script will have its own dedicated folder containing:

- The script `.py` file.
- A dedicated virtual environment (venv).
- Any other necessary files required for execution.

A proper cleanup function will be implemented to remove unused scripts and dependencies.

---

## **Features**

### **Core Features**

#### **Script Management**

Users can:

- Create new Python scripts via a built-in editor.
- Edit existing scripts.
- Delete scripts that are no longer needed.
- Tag scripts for categorization and search.

#### **Dependency Management**

Each script can:

- Define its own pip dependencies.
- Use a dedicated virtual environment (venv) within its own script folder.
- Check if dependencies are installed.
- Install and update dependencies via the web interface.

#### **Execution**

Scripts can be executed:

- **Manually**: Users can run scripts directly from the web interface, with logs displayed in real time.
- **Scheduled**: Users can set up cron-based schedules for scripts.

Execution logs will be stored with:

- Timestamps.
- Status (success/failure).
- Output messages.

#### **Scheduler**

Users can:

- Define and manage execution schedules.
- View upcoming and past scheduled executions in a calendar or list view.

#### **Logging and Monitoring**

- Real-time logs during script execution.
- Historical logs accessible per script, with search and filter capabilities.

#### **Notifications**

- Optional webhook-based notifications for:
  - Execution completion.
  - Errors during execution.

---

## **Non-Functional Requirements**

### **Performance**

- The system should support simultaneous management of up to 100 scripts.
- Logs should load quickly, even with a history of up to 10,000 executions.

### **Scalability**

- The system should allow for future scaling to support more scripts and concurrent executions.

### **Security**

- All scripts will execute in an isolated environment (e.g., using Docker or virtual environments).
- Dependency installations will be restricted to prevent unauthorized modifications.
- A cleanup function will be implemented to remove outdated or unused scripts and dependencies.

### **Deployability**

- The application must be containerized using Docker, with:
  - Configurable port mappings.
  - Persistent volumes for database and log storage.
- Each script and its dependencies will be stored in a dedicated folder outside the database.
- The database (SQLite) will only be used for metadata such as execution logs, schedules, and tags.

---

## **System Architecture**

### **Frontend**

- **Framework**: React with TailwindCSS.
- **Features**:
  - Interactive code editor (e.g., Monaco Editor) for scripts.
  - Dependency management UI.
  - Real-time log viewer using WebSockets.

### **Backend**

- **Framework**: Python with Flask or FastAPI.
- **Key Components**:
  - Script execution using a secure environment (e.g., subprocess with isolated virtual environments).
  - Cron-based scheduler (cron or APScheduler).
  - API endpoints for script and dependency management.
  - A cleanup function to remove unused scripts and dependencies.

### **Database**

- **SQLite** for local development.
- Used only for metadata such as execution logs, schedules, and tags.

---

## **User Interface Design**

### **Pages and Views**

#### **1. Dashboard**

- Overview of:
  - Number of scripts.
  - Upcoming scheduled executions.
  - Recent execution statuses.

#### **2. Script Management**

- List of scripts with:
  - Search and filter options.
  - Tags and status indicators.
- Actions:
  - Create, edit, or delete scripts.

#### **3. Script Details**

- Code editor with syntax highlighting.
- Dependency manager with:
  - Add/remove pip packages.
  - Display of installed versions.
- Tag management:
  - Add/remove tags.
- Schedule Management:
  - Add/remove schedules.
- Logs view:
  - Filter by status (success/failure).

#### **4. Scheduler**

- List of scheduled executions with options to:
  - Add new schedules (using cron syntax).
  - Edit or delete existing schedules.

#### **5. Settings**

- Configure default dependencies for all scripts.
- Manage application-level configurations (e.g., Docker settings).

---

## **Development Plan**

### **Phase 1: Core Features**

- Build backend services for script management, execution, and logging.
- Create the frontend UI for script creation and execution.
- Integrate a basic scheduler.

### **Phase 2: Enhancements**

- Add real-time log streaming.
- Implement per-script dependency management with dedicated folders and virtual environments.
- Create webhook-based notification functionality.

### **Phase 3: Optimization**

- Optimize database queries for log storage and retrieval.
- Implement a cleanup function for unused scripts and dependencies.
- Improve UI/UX based on user feedback.
- Test and validate Docker deployment.

---

## **Acceptance Criteria**

- Users can create, edit, and delete scripts via the web interface.
- Scripts can define and manage their own dependencies in dedicated folders with venv.
- Scripts can be executed manually, with real-time logs displayed.
- Scheduled executions run reliably and log their outcomes.
- Logs and execution history are accessible and filterable.
- The application runs as a Docker container with persistent storage.


# Task Checklist: PolicyPulse Build

This document outlines the step-by-step build tasks to implement PolicyPulse. Every task is designed to be executed by **Claude Code** in a single tool-call iteration.

---

## Phase 1: Backend Foundation

- [ ] **Task 1.1**: Initialize Project Structure and Configurations
  - **Dependencies**: None
  - **Files Touched**:
    - `[NEW] backend/.gitignore`
    - `[NEW] backend/requirements.txt`
    - `[NEW] backend/Procfile`
    - `[NEW] backend/.env.example`
  - **Acceptance Criteria**: Files exist. `requirements.txt` specifies `fastapi`, `uvicorn`, `google-generativeai`, `pydantic`, and `python-dotenv`. `Procfile` is configured for Render.

- [ ] **Task 1.2**: Create Mock Database and Audit Trail Files
  - **Dependencies**: Task 1.1
  - **Files Touched**:
    - `[NEW] backend/mock_db.json`
    - `[NEW] backend/mock_db.bak.json`
    - `[NEW] backend/action_log.json`
  - **Acceptance Criteria**: `mock_db.json` and `mock_db.bak.json` contain the baseline database JSON (pricing rules, campaigns, metrics, customers). `action_log.json` contains `[]`.

- [ ] **Task 1.3**: Implement Gemini Client Wrapper
  - **Dependencies**: Task 1.1
  - **Files Touched**:
    - `[NEW] backend/gemini_client.py`
  - **Acceptance Criteria**: A python module that reads `GEMINI_API_KEY` from environment variables, instantiates `google.generativeai` client, implements a robust model calling function with temperature=0.1, robust JSON cleaning to strip markdown backticks, and exponential backoff retry.

- [ ] **Task 1.4**: Setup FastAPI App and Basic Endpoints
  - **Dependencies**: Task 1.2, Task 1.3
  - **Files Touched**:
    - `[NEW] backend/main.py`
  - **Acceptance Criteria**: Core FastAPI app running with CORS wildcard origins enabled. Implements `/health`, `/state` (reads `mock_db.json`), `/log` (reads `action_log.json`), and `/reset` (overwrites `mock_db.json` with contents of `mock_db.bak.json` and truncates `action_log.json`). Server runs on port `8000`.

---

## Phase 2: Agent Implementation

- [ ] **Task 2.1**: Implement Base Agent class and Pydantic Schemas
  - **Dependencies**: Task 1.4
  - **Files Touched**:
    - `[NEW] backend/agents/__init__.py`
    - `[NEW] backend/agents/base_agent.py`
  - **Acceptance Criteria**: `base_agent.py` defines the abstract base structure of an agent (takes model client, formats prompt, issues call, parses output). Contains all Pydantic validation schemas for all 6 agents (Orchestrator, Ingestion, Insight, Impact, Action, Execution) as specified in `implementation_plan.md`.

- [ ] **Task 2.2**: Implement Orchestrator and Ingestion Agents
  - **Dependencies**: Task 2.1
  - **Files Touched**:
    - `[NEW] backend/agents/orchestrator_agent.py`
    - `[NEW] backend/agents/ingestion_agent.py`
  - **Acceptance Criteria**: Modules implement their respective LLM calls using prompts from `agent-system-prompts.md`. Outputs validate against their Pydantic models.

- [ ] **Task 2.3**: Implement Insight and Impact Agents
  - **Dependencies**: Task 2.2
  - **Files Touched**:
    - `[NEW] backend/agents/insight_agent.py`
    - `[NEW] backend/agents/impact_agent.py`
  - **Acceptance Criteria**: Modules implement their respective LLM calls. The Impact agent accepts the current state of `mock_db.json` and performs calculations against operational metrics.

- [ ] **Task 2.4**: Implement Action and Execution Agents
  - **Dependencies**: Task 2.3
  - **Files Touched**:
    - `[NEW] backend/agents/action_agent.py`
    - `[NEW] backend/agents/execution_agent.py`
  - **Acceptance Criteria**: Action agent returns ranked mitigation structures. Execution Agent modifies the physical `mock_db.json` file, generates a JSON diff showing the path modified, and writes the audit log entry to `action_log.json`.

- [ ] **Task 2.5**: Wire Pipeline into FastAPI `/analyze` Endpoint
  - **Dependencies**: Task 2.4
  - **Files Touched**:
    - `[MODIFY] backend/main.py`
  - **Acceptance Criteria**: `/analyze` accepts the unstructured input text, executes the Orchestrator, conditionalizes further execution on `should_halt`, runs specialist agents sequentially, captures durations, outputs the combined `PipelineResponse` JSON, and handles concurrency with an async lock.

---

## Phase 3: Flutter Application

- [ ] **Task 3.1**: Initialize Flutter App and Dependencies
  - **Dependencies**: None
  - **Files Touched**:
    - `[NEW] mobile/pubspec.yaml`
    - `[NEW] mobile/android/app/build.gradle`
  - **Acceptance Criteria**: Standard Flutter configuration. `pubspec.yaml` includes `http` and `provider`. `build.gradle` has `minSdkVersion` set to at least `21`.

- [ ] **Task 3.2**: Implement App Theme, Config and Data Models
  - **Dependencies**: Task 3.1
  - **Files Touched**:
    - `[NEW] mobile/lib/theme.dart`
    - `[NEW] mobile/lib/config.dart`
    - `[NEW] mobile/lib/models/agent_result.dart`
    - `[NEW] mobile/lib/models/pipeline_response.dart`
  - **Acceptance Criteria**: Theme defines deep slate background `#0B0F17` and glassmorphic card stylings. Config exports `API_BASE_URL` pointing to localhost backend. Models successfully parse incoming FastAPI response JSON.

- [ ] **Task 3.3**: Create API Connection Service
  - **Dependencies**: Task 3.2
  - **Files Touched**:
    - `[NEW] mobile/lib/services/api_service.dart`
  - **Acceptance Criteria**: API service handles HTTP POST to `/analyze`, GET to `/state`, GET to `/log`, and POST to `/reset`. Integrates standard error-catching and notifies subscribers via `ChangeNotifier`.

- [ ] **Task 3.4**: Implement Dashboard (Home) Screen
  - **Dependencies**: Task 3.3
  - **Files Touched**:
    - `[NEW] mobile/lib/screens/home_screen.dart`
    - `[MODIFY] mobile/lib/main.dart`
  - **Acceptance Criteria**: Main dashboard showing Scenario A and Scenario B quick buttons, a text box for custom inputs, database inspector links, and a prominent "Trigger Pipeline" button. `main.dart` boots this screen.

- [ ] **Task 3.5**: Implement Live Pipeline Thinking Timeline Screen
  - **Dependencies**: Task 3.4
  - **Files Touched**:
    - `[NEW] mobile/lib/screens/pipeline_screen.dart`
  - **Acceptance Criteria**: Dynamic list of card widgets, one for each agent. Displays state: pending, processing (with progress indicator), and completed (showing summary reasoning + confidence).

- [ ] **Task 3.6**: Implement Results and Diff Screen
  - **Dependencies**: Task 3.5
  - **Files Touched**:
    - `[NEW] mobile/lib/screens/result_screen.dart`
  - **Acceptance Criteria**: Visualizes the executed action, shows before/after database changes in a clear comparison matrix, lists the generated audit ID, and features a "Reset State" button.

---

## Phase 4: Deployment & Release

- [ ] **Task 4.1**: Set Up Local Tunnel (ngrok) and Environment Tests
  - **Dependencies**: Task 2.5
  - **Files Touched**: None
  - **Acceptance Criteria**: Launch ngrok tunnel locally, verify that hitting the public ngrok endpoint triggers the backend on `localhost:8000` and executes a sample payload.

- [ ] **Task 4.2**: Deploy Backend to Render
  - **Dependencies**: Task 4.1
  - **Files Touched**: None
  - **Acceptance Criteria**: Create Render web service from GitHub repository, set `GEMINI_API_KEY` env var, and verify public URL returns `{ "status": "ok" }` on health endpoint.

- [ ] **Task 4.3**: Compile Production Android Package (APK)
  - **Dependencies**: Task 3.6, Task 4.2
  - **Files Touched**:
    - `[MODIFY] mobile/lib/config.dart`
  - **Acceptance Criteria**: Swap `API_BASE_URL` in `config.dart` to point to the production Render URL. Build APK using `flutter build apk --release`. Output APK file exists and installs successfully on target device.

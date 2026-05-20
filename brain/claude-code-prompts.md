# Claude Code copy-paste Prompts for PolicyPulse

This file contains the complete list of self-contained prompts to paste directly into **Claude Code** in the terminal. Each prompt contains all context, schema blueprints, and verification routines to allow Claude Code to implement files from scratch without prior conversation context.

---

# Phase 1: Backend Foundation

## Task 1.1: Initialize Project Structure and Configurations
**Phase:** 1  
**Estimated time:** 5 minutes  
**Files touched:**  
- `backend/.gitignore`
- `backend/requirements.txt`
- `backend/Procfile`
- `backend/.env.example`

**Prompt for Claude Code (copy below, paste in terminal):**
```text
Initialize the backend workspace directory under "backend/".
Create the following files with these exact requirements:

1. Create backend/.gitignore:
Exclude: .env, __pycache__/, *.pyc, *.pyo, .pytest_cache/, mock_db.json, action_log.json

2. Create backend/requirements.txt:
Add:
fastapi==0.111.0
uvicorn==0.30.1
google-generativeai==0.7.1
pydantic==2.7.2
python-dotenv==1.0.1
tenacity==8.3.0

3. Create backend/Procfile:
Add: web: uvicorn main:app --host 0.0.0.0 --port $PORT

4. Create backend/.env.example:
Add: GEMINI_API_KEY=your_key_here
```

**Expected output:** Four files created in the `backend/` directory.  
**Verification command:** Check if directory structure is correct.  
`dir backend`  
**If it fails:** Ensure path names are relative to the project root.

---

## Task 1.2: Create Mock Database and Audit Trail Files
**Phase:** 1  
**Estimated time:** 5 minutes  
**Files touched:**  
- `backend/mock_db.json`
- `backend/mock_db.bak.json`
- `backend/action_log.json`

**Prompt for Claude Code (copy below, paste in terminal):**
```text
Create the database mock files inside backend/ to simulate our business state.

1. Create backend/mock_db.json and backend/mock_db.bak.json (must contain exact duplicates of this initial state):
{
  "pricing_rules": {
    "base_delivery_fee": 150,
    "free_delivery_threshold": 1500,
    "delivery_surcharges": []
  },
  "campaigns": [
    {
      "campaign_id": "std_welcome",
      "name": "Standard Welcome Campaign",
      "region": "all",
      "discount_pct": 10.0,
      "active": true
    }
  ],
  "operational_metrics": {
    "active_skus": 234,
    "daily_orders": 1200,
    "avg_ticket_size_pkr": 1100
  },
  "customers": [
    {
      "id": "cust-01",
      "name": "Ali Khan",
      "region": "Lahore",
      "orders_last_30_days": 12,
      "last_order_val_pkr": 950
    },
    {
      "id": "cust-02",
      "name": "Zainab Bibi",
      "region": "Lahore",
      "orders_last_30_days": 3,
      "last_order_val_pkr": 400
    },
    {
      "id": "cust-03",
      "name": "Bilal Ahmed",
      "region": "Karachi",
      "orders_last_30_days": 8,
      "last_order_val_pkr": 1200
    },
    {
      "id": "cust-04",
      "name": "Fatima Sana",
      "region": "Islamabad",
      "orders_last_30_days": 15,
      "last_order_val_pkr": 1800
    }
  ]
}

2. Create backend/action_log.json:
Must start as an empty list: []
```

**Expected output:** Three JSON files created.  
**Verification command:** Parse files using a utility to check format.  
`python -m json.tool backend/mock_db.json`  
**If it fails:** Ensure JSON structure is valid (no stray commas).

---

## Task 1.3: Implement Gemini Client Wrapper
**Phase:** 1  
**Estimated time:** 10 minutes  
**Files touched:**  
- `backend/gemini_client.py`

**Prompt for Claude Code (copy below, paste in terminal):**
```text
Write a robust wrapper for Google Gemini API under backend/gemini_client.py.

Requirements:
- Read GEMINI_API_KEY using dotenv or os.environ.
- Initialize google.generativeai client.
- Expose a function: generate_response(prompt: str, system_instruction: str = None, temperature: float = 0.1) -> str.
- Add retries with exponential backoff using tenacity.
- Handle formatting: The models occasionally wrap JSON outputs inside Markdown tags (```json ... ```). The generate_response function must clean the raw text: if it starts with ```json or ```, strip these decorators and trailing backticks to return a raw JSON string.
- Provide clean logs showing duration and token execution errors.
```

**Expected output:** `backend/gemini_client.py` created.  
**Verification command:** Create a quick temporary script to test client with a basic prompt, or verify imports and syntax.  
`python -c "import os; os.environ['GEMINI_API_KEY']='test'; import gemini_client"`  
**If it fails:** Install google-generativeai package if not present (`pip install google-generativeai tenacity python-dotenv`).

---

## Task 1.4: Setup FastAPI App and Basic Endpoints
**Phase:** 1  
**Estimated time:** 10 minutes  
**Files touched:**  
- `backend/main.py`

**Prompt for Claude Code (copy below, paste in terminal):**
```text
Create the baseline FastAPI app in backend/main.py.

Requirements:
- Set up FastAPI app with CORS middleware (allow all origins, credentials, methods, headers).
- Expose GET /health -> returns {"status": "ok", "timestamp": "ISO8601 current time"}
- Expose GET /state -> returns contents of mock_db.json. Return 500 error if file not found.
- Expose GET /log -> returns contents of action_log.json. Return 500 if not found.
- Expose POST /reset -> copies mock_db.bak.json content to mock_db.json, overwrites action_log.json with [], and returns {"status": "reset_successful", "timestamp": "..."}
- Run uvicorn on localhost:8000.
```

**Expected output:** `backend/main.py` containing health, state, log, and reset routes.  
**Verification command:** Start the server and run Curl requests.  
`uvicorn main:app --reload` (then in another shell: `curl http://localhost:8000/health`)  
**If it fails:** Ensure mock_db.json and mock_db.bak.json exist from Task 1.2.

---

# Phase 2: Agent Implementation

## Task 2.1: Implement Base Agent class and Pydantic Schemas
**Phase:** 2  
**Estimated time:** 15 minutes  
**Files touched:**  
- `backend/agents/__init__.py`
- `backend/agents/base_agent.py`

**Prompt for Claude Code (copy below, paste in terminal):**
```text
Create the base agent architecture in backend/agents/.

1. Create backend/agents/__init__.py to export all agents (empty placeholder for now).
2. Create backend/agents/base_agent.py:
   - Define a BaseAgent class that takes a Gemini client wrapper and system instruction template.
   - Define Pydantic response structures for all pipeline agents:
     - AgentResponseBase (fields: agent_name: str, confidence: float, reasoning: str, timestamp: str)
     - OrchestratorResponse (AgentResponseBase + output: OrchestratorOutput with should_halt: bool, reason: str, agents_invoked: List[str])
     - IngestionResponse (AgentResponseBase + output: IngestionOutput with event_type: str, magnitude_pct: float, effective_date: str, scope: str, details: Dict[str, Any])
     - InsightResponse (AgentResponseBase + output: InsightOutput with primary_driver: str, operational_bottleneck: str, severity: str, qualitative_assessment: str)
     - ImpactResponse (AgentResponseBase + output: ImpactOutput with affected_skus: int, affected_daily_orders: int, projected_daily_loss_pkr: float, margin_compression_pct: float)
     - ActionResponse (AgentResponseBase + output: List[BusinessAction] where BusinessAction has rank: int, action_id: str, description: str, recovery_potential_pkr: float, tradeoff: str, system_update: Dict[str, Any])
     - ExecutionResponse (AgentResponseBase + output: ExecutionOutput with action_taken: str, before_state: Dict[str, Any], after_state: Dict[str, Any], diff: List[Dict[str, Any]], log_entry_id: str)
     
Ensure Pydantic schemas enforce float ranges or list shapes. Refer to the specifications in brain/implementation_plan.md.
```

**Expected output:** `backend/agents/base_agent.py` containing Pydantic schemas.  
**Verification command:** Run syntax check.  
`python -c "from agents.base_agent import IngestionResponse"`  
**If it fails:** Double check import paths and pydantic syntax.

---

## Task 2.2: Implement Orchestrator and Ingestion Agents
**Phase:** 2  
**Estimated time:** 15 minutes  
**Files touched:**  
- `backend/agents/orchestrator_agent.py`
- `backend/agents/ingestion_agent.py`

**Prompt for Claude Code (copy below, paste in terminal):**
```text
Implement the Orchestrator and Ingestion agents.

1. Create backend/agents/orchestrator_agent.py:
   - Inherits BaseAgent.
   - Embeds Orchestrator system prompt from brain/agent-system-prompts.md.
   - Method: run(text: str) -> OrchestratorResponse.
   - Evaluates if text is relevant. Returns Halt decision or specialist list.

2. Create backend/agents/ingestion_agent.py:
   - Inherits BaseAgent.
   - Embeds Ingestion system prompt from brain/agent-system-prompts.md.
   - Method: run(text: str) -> IngestionResponse.
   - Parses metrics/facts into structural details keys.
```

**Expected output:** Two agent files created.  
**Verification command:** Import them in python shell to verify compilation.  
`python -c "from agents.orchestrator_agent import OrchestratorAgent; from agents.ingestion_agent import IngestionAgent"`  
**If it fails:** Ensure base_agent is fully typed and imported correctly.

---

## Task 2.3: Implement Insight and Impact Agents
**Phase:** 2  
**Estimated time:** 15 minutes  
**Files touched:**  
- `backend/agents/insight_agent.py`
- `backend/agents/impact_agent.py`

**Prompt for Claude Code (copy below, paste in terminal):**
```text
Implement the Insight and Impact agents.

1. Create backend/agents/insight_agent.py:
   - Inherits BaseAgent.
   - Embeds Insight system prompt from brain/agent-system-prompts.md.
   - Method: run(raw_text: str, ingestion_output: Dict) -> InsightResponse.
   - Contextualizes qualitative drivers and severity.

2. Create backend/agents/impact_agent.py:
   - Inherits BaseAgent.
   - Embeds Impact system prompt from brain/agent-system-prompts.md.
   - Method: run(ingestion_output: Dict, insight_output: Dict, current_db_state: Dict) -> ImpactResponse.
   - Calculates SKU exposure, orders affected, daily PKR loss, and margin compression using the current db state.
```

**Expected output:** Two agent files created.  
**Verification command:** Check python imports.  
`python -c "from agents.insight_agent import InsightAgent; from agents.impact_agent import ImpactAgent"`  
**If it fails:** Ensure previous agents are imported correctly.

---

## Task 2.4: Implement Action and Execution Agents
**Phase:** 2  
**Estimated time:** 20 minutes  
**Files touched:**  
- `backend/agents/action_agent.py`
- `backend/agents/execution_agent.py`

**Prompt for Claude Code (copy below, paste in terminal):**
```text
Implement the Action and Execution agents.

1. Create backend/agents/action_agent.py:
   - Inherits BaseAgent.
   - Embeds Action system prompt from brain/agent-system-prompts.md.
   - Method: run(ingestion: Dict, insight: Dict, impact: Dict, db_state: Dict) -> ActionResponse.
   - Formulates and ranks 3 actions. Embeds 'system_update' directives.

2. Create backend/agents/execution_agent.py:
   - Inherits BaseAgent.
   - Embeds Execution system prompt from brain/agent-system-prompts.md.
   - Method: run(top_action: Dict, current_db_state: Dict) -> ExecutionResponse.
   - Mutates database: reads mock_db.json, applies changes to pricing_rules or campaigns based on 'system_update', saves mock_db.json, appends log entry to action_log.json, computes JSON diff.
   
Ensure Execution Agent performs actual file writes to disk. Use file locks if needed, or serialize write operations.
```

**Expected output:** Action and Execution agent classes implemented.  
**Verification command:** Verify execution file write.  
`python -c "from agents.execution_agent import ExecutionAgent"`  
**If it fails:** Check JSON patch paths and file writing permissions.

---

## Task 2.5: Wire Pipeline into FastAPI /analyze Endpoint
**Phase:** 2  
**Estimated time:** 15 minutes  
**Files touched:**  
- `backend/main.py`
- `backend/agents/__init__.py`

**Prompt for Claude Code (copy below, paste in terminal):**
```text
Modify backend/main.py to implement the pipeline execution.

1. Update backend/agents/__init__.py to export all agents.
2. In backend/main.py:
   - Import all agents.
   - Instantiate agents sharing a single Gemini Client wrapper instance.
   - Create an async Lock: database_write_lock = asyncio.Lock() to avoid file read/write overlaps.
   - Expose POST /analyze endpoint receiving AnalyzeRequest.
   - Execute Orchestrator. If should_halt is true, bypass specialists and return immediately.
   - Run Ingestion -> Insight -> Impact -> Action -> Execution sequentially.
   - Wrap execution steps in time captures. Compute elapsed step durations.
   - If Execution succeeds, apply changes to mock_db.json and log to action_log.json under the database_write_lock.
   - Return PipelineResponse JSON conforming to the contract schema in brain/implementation_plan.md.
```

**Expected output:** Complete main.py running.  
**Verification command:** Run server and query `/analyze` endpoint with a test prompt.  
`python -m uvicorn main:app --reload`  
**If it fails:** Double check pydantic validations on response payload formats.

---

# Phase 3: Flutter Application

## Task 3.1: Initialize Flutter App and Dependencies
**Phase:** 3  
**Estimated time:** 10 minutes  
**Files touched:**  
- `mobile/pubspec.yaml`
- `mobile/android/app/build.gradle`

**Prompt for Claude Code (copy below, paste in terminal):**
```text
Initialize the Flutter project configurations.

1. In mobile/pubspec.yaml, replace dependencies with:
dependencies:
  flutter:
    sdk: flutter
  cupertino_icons: ^1.0.6
  http: ^1.2.1
  provider: ^6.1.2

2. In mobile/android/app/build.gradle:
Ensure defaultconfig.minSdkVersion is set to 21 or higher.

Run "flutter pub get" inside mobile/ directory to fetch packages.
```

**Expected output:** Packages fetched, minSdk updated.  
**Verification command:** Run pub get and check return code.  
`cd mobile && flutter pub get`  
**If it fails:** Ensure flutter path is in local path environment.

---

## Task 3.2: Implement App Theme, Config and Data Models
**Phase:** 3  
**Estimated time:** 15 minutes  
**Files touched:**  
- `mobile/lib/theme.dart`
- `mobile/lib/config.dart`
- `mobile/lib/models/agent_result.dart`
- `mobile/lib/models/pipeline_response.dart`

**Prompt for Claude Code (copy below, paste in terminal):**
```text
Create configurations and model mappings inside mobile/lib/.

1. Create mobile/lib/config.dart:
Add: const String API_BASE_URL = "http://10.0.2.2:8000"; // android emulator mapping for localhost

2. Create mobile/lib/theme.dart:
Define visual guidelines:
- dark slate background: Color(0xFF0B0F17)
- dark grey glass card background: Color(0xFF151F32)
- primary electric blue: Color(0xFF3B82F6)
- success emerald: Color(0xFF10B981)
- warning amber: Color(0xFFF59E0B)
- text details: Color(0xFFE2E8F0)

3. Create mobile/lib/models/agent_result.dart:
Representation of individual agent outputs (agent_name, confidence, reasoning, timestamp, dynamic output data).

4. Create mobile/lib/models/pipeline_response.dart:
Container that parses the complete FastAPI /analyze output including orchestrator, and optional ingestion, insight, impact, actions, execution fields, durations list, and total elapsed duration.
```

**Expected output:** Models and theme created.  
**Verification command:** Verify compilation by running a quick analysis check.  
`flutter analyze`  
**If it fails:** Ensure correct imports of package types.

---

## Task 3.3: Create API Connection Service
**Phase:** 3  
**Estimated time:** 15 minutes  
**Files touched:**  
- `mobile/lib/services/api_service.dart`

**Prompt for Claude Code (copy below, paste in terminal):**
```text
Create mobile/lib/services/api_service.dart.

Requirements:
- Inherit ChangeNotifier.
- Expose methods:
  - Future<PipelineResponse?> analyzeIncident(String text, String scenarioHint)
  - Future<Map<String, dynamic>?> fetchDbState()
  - Future<List<dynamic>?> fetchActionLogs()
  - Future<bool> resetDatabase()
- Implement JSON parsing, exception handlers, and dynamic state updates.
- Track loading states (bool isProcessing).
```

**Expected output:** `api_service.dart` networking class written.  
**Verification command:** Run analysis checks.  
`flutter analyze`  
**If it fails:** Check imports and asynchronous future formats.

---

## Task 3.4: Implement Dashboard (Home) Screen
**Phase:** 3  
**Estimated time:** 20 minutes  
**Files touched:**  
- `mobile/lib/screens/home_screen.dart`
- `mobile/lib/main.dart`

**Prompt for Claude Code (copy below, paste in terminal):**
```text
Build the Home Dashboard Screen.

1. Create mobile/lib/screens/home_screen.dart:
   - Provide scenario selection buttons:
     - "Scenario A: Nationwide Fuel Price Hike" (prefills input text box with Scenario A text: "The Government of Pakistan announced today a 15% increase in fuel prices effective Monday...")
     - "Scenario B: Lahore sales drop" (prefills with Scenario B text: "Internal sales report — Week 21: Lahore region orders dropped 25%...")
   - A multi-line text input field for custom text documents.
   - An interactive trigger button: "TRIGGER ANALYSIS PIPELINE".
   - Links to open floating modal sheet inspectors for "View Current DB State" and "View Action Audit Trail".
   - A reset button to flush database state.

2. Modify mobile/lib/main.dart:
   - Standard MaterialApp configuration.
   - Set home as HomeScreen.
   - Wrap the App inside MultiProvider containing ApiService.
```

**Expected output:** UI dashboard operational.  
**Verification command:** Perform static validation.  
`flutter analyze`  
**If it fails:** Check Provider import declarations.

---

## Task 3.5: Implement Live Pipeline Thinking Timeline Screen
**Phase:** 3  
**Estimated time:** 20 minutes  
**Files touched:**  
- `mobile/lib/screens/pipeline_screen.dart`

**Prompt for Claude Code (copy below, paste in terminal):**
```text
Build the Pipeline screen: mobile/lib/screens/pipeline_screen.dart.

Requirements:
- Screen triggered when analyze is running.
- Displays a vertical progress timeline (stepper-style list) representing the 6 agents:
  - Orchestrator, Ingestion, Insight, Impact, Action, Execution.
- State representations:
  - Pending (Greyed out, locked)
  - Processing (Spinning accent loading indicator, glowing borders)
  - Complete (Green checkmark, prints confidence, expands card on click to show the agent's 2-3 sentence reasoning and raw output)
- Stream local logging information at the bottom of the screen (mock or captured logging print lines).
- Auto-navigate to ResultScreen once the Execution Agent step completes.
```

**Expected output:** Pipeline execution screen complete.  
**Verification command:** Verify compilation.  
`flutter analyze`  
**If it fails:** Ensure state updates trigger widget rebuilds.

---

## Task 3.6: Implement Results and Diff Screen
**Phase:** 3  
**Estimated time:** 20 minutes  
**Files touched:**  
- `mobile/lib/screens/result_screen.dart`

**Prompt for Claude Code (copy below, paste in terminal):**
```text
Build the Results Screen: mobile/lib/screens/result_screen.dart.

Requirements:
- Displays summary of Selected Action (Rank 1).
- Shows confidence levels and elapsed times.
- Contains a State Diff visual table comparing pricing rules/campaign values *before* and *after* execution (retrieved from pipeline execution response diff).
- Renders the generated event ID and audit log details.
- Provide a primary button: "Reset Database State" which performs API reset call and redirects back to Home Dashboard.
```

**Expected output:** Results UI screen compiled.  
**Verification command:** Analyze layout.  
`flutter analyze`  
**If it fails:** Ensure route argument unpacking handles pipeline results safely.

---

# Phase 4: Deployment & Release

## Task 4.1: Set Up Local Tunnel (ngrok) and Environment Tests
**Phase:** 4  
**Estimated time:** 10 minutes  
**Files touched:** None

**Prompt for Claude Code (copy below, paste in terminal):**
```text
Expose the backend using ngrok and test the tunnel.

Requirements:
- Verify FastAPI backend is running locally on port 8000.
- Execute "ngrok http 8000" in the command line (assuming ngrok is pre-installed) to generate a public HTTPS endpoint.
- Verify the public endpoint is reachable by sending a cURL GET to the health path:
  curl <YOUR_NGROK_HTTPS_URL>/health
- Document the endpoint in a temporary workspace log.
```

**Expected output:** Live ngrok tunnel exposed.  
**Verification command:** Request health check via curl on public URL.  
**If it fails:** Ensure ngrok is authenticated or check firewall options.

---

## Task 4.2: Deploy Backend to Render
**Phase:** 4  
**Estimated time:** 15 minutes  
**Files touched:** None

**Prompt for Claude Code (copy below, paste in terminal):**
```text
Prepare deploy commands for Render.com.

Requirements:
- Check git repository status to confirm backend/, requirements.txt, and Procfile are staged.
- Ensure Procfile states: web: uvicorn main:app --host 0.0.0.0 --port $PORT
- Outline steps to deploy: create a Web Service in Render dashboard, link the repository, choose Python environment, set build command: "pip install -r backend/requirements.txt", start command: "uvicorn backend.main:app --host 0.0.0.0 --port $PORT" (adjust folder root if needed), and inject environment variable: GEMINI_API_KEY.
- Output verify checklist for Render.
```

**Expected output:** Deploy configuration finalized.  
**Verification command:** Inspect Render settings.  
**If it fails:** Adjust root directory path parameters in Render settings.

---

## Task 4.3: Compile Production Android Package (APK)
**Phase:** 4  
**Estimated time:** 15 minutes  
**Files touched:**  
- `mobile/lib/config.dart`

**Prompt for Claude Code (copy below, paste in terminal):**
```text
Compile final APK for mobile devices.

Requirements:
- Modify mobile/lib/config.dart to point API_BASE_URL to the production Render URL.
- Execute clean command: flutter clean
- Run pub get: flutter pub get
- Compile APK: flutter build apk --release
- Verify APK outputs in build/app/outputs/flutter-apk/app-release.apk.
```

**Expected output:** Production release APK generated.  
**Verification command:** Verify file exists and has size > 5MB.  
`dir mobile\build\app\outputs\flutter-apk\app-release.apk`  
**If it fails:** Ensure flutter gradle build files align and JVM is present.

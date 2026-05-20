# PolicyPulse: Autonomous Content-to-Action Agent System
### Google Antigravity Hackathon (Challenge 1: Autonomous Content-to-Action Agent)

PolicyPulse is an end-to-end mobile application and multi-agent backend that consumes unstructured business documents (news articles, regional sales logs, policy updates) and automatically makes operational decisions, simulates executions on a mock business state on disk, generates clear visual changes, and records actions in a persistent audit trail.

---

## Repository Structure

```
policypulse/
├── backend/
│   ├── main.py                       # FastAPI application, CORS configs, routing
│   ├── requirements.txt              # Python requirements
│   ├── Procfile                      # Web server configuration for Render deployment
│   ├── mock_db.json                  # Active mock business database state file
│   ├── mock_db.bak.json              # Immutable backup state (read during reset)
│   ├── action_log.json               # Persistent action audit log file
│   ├── .env.example                  # Environment template containing GEMINI_API_KEY
│   ├── .gitignore                    # Python git ignore configurations
│   ├── gemini_client.py              # Central Gemini wrapper with fallback & retry logic
│   └── agents/
│       ├── __init__.py               # Package initializer
│       ├── base_agent.py             # Abstract base agent class defining common interface
│       ├── orchestrator_agent.py     # Relevance check & router agent
│       ├── ingestion_agent.py        # Entity/Metric extractor
│       ├── insight_agent.py          # Qualitative analyzer
│       ├── impact_agent.py           # Quantitative financial/SKU calculator
│       ├── action_agent.py           # Multi-option action generator & ranker
│       └── execution_agent.py        # DB patcher & diff generator
├── mobile/
│   ├── pubspec.yaml                  # Flutter package definition (http, provider, etc.)
│   ├── lib/
│   │   ├── main.dart                 # Application entry point & MaterialApp bootstrap
│   │   ├── config.dart               # API Server URL configurations (switchable)
│   │   ├── theme.dart                # Slate HSL dark mode styles and input styles
│   │   ├── models/
│   │   │   ├── agent_result.dart     # Typed representation of individual agent outputs
│   │   │   └── pipeline_response.dart# Container class parsing the entire analyze response
│   │   ├── services/
│   │   │   └── api_service.dart      # HTTP client wrapper (analyze, state, reset, health)
│   │   └── screens/
│   │       ├── home_screen.dart      # Input terminal with scenario selection
│   │       ├── pipeline_screen.dart  # Visual thinking cards timeline
│   │       └── result_screen.dart    # Detailed before/after diff grid and audit viewer
│   └── android/
│       └── app/
│           └── build.gradle          # Build settings ensuring minSdk >= 21
└── brain/
    ├── implementation_plan.md        # Detailed architecture document
    ├── agent-system-prompts.md       # Verbatim LLM prompt architectures
    ├── task.md                       # Task checklist containing acceptance criteria
    ├── claude-code-prompts.md        # Explicit instruction prompts for Claude terminal calls
    ├── walkthrough.md                # Post-mortem and verification walkthrough
    └── claude-code-sessions/         # Log storage for Claude CLI transcripts
```

---

## Tech Stack
* **Frontend**: Flutter (Min SDK >= 21)
* **Backend**: Python 3.12 + FastAPI + Uvicorn ASGI
* **LLM**: Google Gemini 2.5 Flash via `google-generativeai` SDK
* **State Store**: Flat JSON database files (`mock_db.json` and `action_log.json`)

---

## Local Setup & Quick Start

### 1. Backend Setup
1. Navigate to the backend directory:
   ```bash
   cd backend
   ```
2. Create a virtual environment and activate it:
   ```bash
   python -m venv venv
   # On Windows:
   venv\Scripts\activate
   # On Linux/macOS:
   source venv/bin/activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Copy the environment template and set your Gemini API key:
   ```bash
   cp .env.example .env
   # Edit backend/.env to define your GEMINI_API_KEY
   ```
5. Launch the FastAPI server:
   ```bash
   uvicorn main:app --reload
   ```
6. Verify server is running by opening: `http://localhost:8000/health` or checking OpenAPI docs at `http://localhost:8000/docs`.

### 2. Tunnel Setup (For Physical Phone Testing)
Expose the backend using `ngrok` so the USB-connected device can talk to localhost:
```bash
ngrok http 8000
```
Copy the public `https://<random-id>.ngrok-free.app` URL.

### 3. Mobile Setup
1. Navigate to the mobile directory:
   ```bash
   cd mobile
   ```
2. Configure API settings in `lib/config.dart`:
   - Set `API_BASE_URL` to your active ngrok tunnel URL (or leave it as `http://10.0.2.2:8000` for Android Studio Emulator).
3. Fetch dependencies:
   ```bash
   flutter pub get
   ```
4. Connect your Android phone via USB (with Developer Mode and USB Debugging enabled) and run:
   ```bash
   flutter run
   ```
5. Compile final release package:
   ```bash
   flutter build apk --release
   ```
   The output is saved to `build/app/outputs/flutter-apk/app-release.apk`.

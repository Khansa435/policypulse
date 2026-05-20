# PolicyPulse: Autonomous Content-to-Action Agent System
## Comprehensive Implementation Plan & Architectural Blueprint
### Google Antigravity Hackathon (Challenge 1: Autonomous Content-to-Action Agent)

---

## 1. Project Overview

PolicyPulse is an autonomous content-to-action agent system built to bridge the gap between incoming unstructured data and immediate operational execution. In any business, critical decisions are often delayed by the time it takes for humans to read articles or internal reports, analyze their impact, determine actions, and manually reconfigure systems. PolicyPulse automates this entire loop in a secure, transparent, and auditable manner.

The system is designed with a cooperative multi-agent pipeline at its core. It ingests raw, unstructured text (news articles, regional sales summaries, policy updates), parses the text into structured signals, reasons about the operational meaning, assesses financial/systemic impacts, generates and ranks mitigation strategies, and simulates the top action by modifying a mock database file on disk. The system produces a detailed state diff and records the action in an audit log.

A beautiful Flutter mobile application displays this entire lifecycle. Users can trigger scenarios, watch a live timeline showing each agent's reasoning, duration, and confidence scores, and inspect before/after database states. The Python FastAPI backend runs the pipeline using Gemini 2.5 Flash via the official `google-generativeai` SDK.

---

## 2. Hackathon Evaluation Criteria Mapping

This project is structured specifically to maximize scores across the hackathon's grading rubrics:

### A. Use of Antigravity (25% of score)
* **Design & Planning**: Antigravity orchestrates the planning phase, designing the schemas, agent logic, and interfaces.
* **Structured Handoff**: Antigravity writes the complete system prompts, code task files, and copy-pasteable scripts for Claude Code.
* **Traceability**: All agent logs and task.md updates are tracked inside this workspace, serving as a live diary of the agentic development lifecycle.

### B. Agentic Reasoning (20% of score)
* **6-Agent Sequential Pipeline**: Rather than a single massive prompt, we separate concerns across six specialized agents.
* **Confidence & Explanation**: Every agent is forced by its system prompt to output an honest confidence score (0.0 to 1.0) and write a 2-3 sentence reasoning chain explaining its choice.
* **No Hardcoding**: The Orchestrator Agent is an LLM agent that decides whether to run the pipeline, halt, or route differently.

### C. Insight & Decision Quality (20% of score)
* **Context-Aware Recommendations**: The Impact and Action agents read the actual state of the business (`mock_db.json`) before reasoning. For instance, in a fuel hike scenario, the Action agent doesn't suggest a generic price raise; it calculates margin compression on the current active order sizes and applies a surcharge to orders below a specific value.
* **Few-Shot Prompting**: Each agent has detailed operational examples in its system prompt to ensure precise output structures.

### D. Action Simulation (15% of score)
* **Real File Mutator**: The Execution Agent uses Python to load, mutate, and write to `mock_db.json`. It computes an RFC 6902-style JSON diff of the exact changes.
* **Audit Trail**: Every execution appends a signed, timestamped entry to `action_log.json`, proving auditability.

### E. Technical Implementation (10% of score)
* **FastAPI Backend**: Built with clean, type-checked Python 3.12, using Pydantic for validation, CORS middleware, and error handlers.
* **Flutter Mobile Client**: Native compiled Dart application built with clean models, services, screens, and custom theme.

### F. Innovation & UX (10% of score)
* **Interactive Timeline**: An animated, step-by-step pipeline execution screen showing "agent thinking" state cards.
* **JSON State Diff Visualizer**: A visual grid/table displaying the specific database parameters changed by the agent's actions.

---

## 3. 6-Agent System Architecture

The pipeline uses a sequential routing pattern where the output of one agent is validated and passed as context to the next.

```
+-----------------------------------------------------------------------------+
|                               Input Document                                |
+-----------------------------------------------------------------------------+
                                       │
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                             Orchestrator Agent                              │
│ - Analyzes relevance to operations.                                         │
│ - Decides whether to run full pipeline or halt.                             │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │ (If Relevant)
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              Ingestion Agent                                │
│ - Parses unstructured text into clean structured metrics/entities.          │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                                Insight Agent                                │
│ - Formulates qualitative operational takeaways from the structured facts.    │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                                Impact Agent                                 │
│ - Reads mock_db.json + Ingestion/Insight.                                   │
│ - Computes quantitative loss, SKU exposure, and order count impact.         │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                                Action Agent                                 │
│ - Proposes and ranks 3 operational actions based on impact and DB state.    │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              Execution Agent                                │
│ - Selects Rank 1 action.                                                    │
│ - Mutates mock_db.json, generates diff, writes to action_log.json.          │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Flow of Context & Shared State
The main backend router (`/analyze`) acts as the state coordinator. It manages the session memory and passes cumulative logs to subsequent agents:
1. `OrchestratorInput` = Raw Text.
2. `IngestionInput` = Raw Text.
3. `InsightInput` = Ingestion Output + Raw Text.
4. `ImpactInput` = Ingestion Output + Insight Output + Current Database State (`mock_db.json`).
5. `ActionInput` = Ingestion Output + Insight Output + Impact Output + Current Database State.
6. `ExecutionInput` = Selected Action + Current Database State.

---

## 4. Backend API Contract & Pydantic Schemas

Below are the exact Pydantic model contracts to be implemented in `backend/main.py` and referenced by the agents.

### Pydantic Models

```python
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional

# Base structures for Agent Response
class AgentResponseBase(BaseModel):
    agent_name: str = Field(..., description="Name of the agent (e.g. 'ingestion')")
    confidence: float = Field(..., description="Confidence score between 0.0 and 1.0")
    reasoning: str = Field(..., description="2-3 sentence explanation of findings and confidence")
    timestamp: str = Field(..., description="ISO8601 timestamp of execution")

# Input Request Schema
class AnalyzeRequest(BaseModel):
    text: str = Field(..., description="The raw unstructured document text to analyze")
    scenario_hint: Optional[str] = Field("auto", description="Hint regarding scenario: 'policy', 'sales', or 'auto'")

# Orchestrator Agent Output
class OrchestratorOutput(BaseModel):
    should_halt: bool = Field(..., description="Whether to stop the pipeline because the input is irrelevant")
    reason: str = Field(..., description="Explanation of why the pipeline should run or halt")
    agents_invoked: List[str] = Field(..., description="List of agent names to invoke if not halting")

class OrchestratorResponse(AgentResponseBase):
    output: OrchestratorOutput

# Ingestion Agent Output
class IngestionOutput(BaseModel):
    event_type: str = Field(..., description="Identified type of event (e.g. 'fuel_price_hike', 'order_decline')")
    magnitude_pct: float = Field(..., description="Percentage change or magnitude extracted")
    effective_date: str = Field(..., description="Extracted date or timeline of when the change occurs")
    scope: str = Field(..., description="Geographical or organizational scope (e.g. 'Lahore', 'nationwide')")
    details: Dict[str, Any] = Field(default_factory=dict, description="Key-value pairs of raw metrics extracted")

class IngestionResponse(AgentResponseBase):
    output: IngestionOutput

# Insight Agent Output
class InsightOutput(BaseModel):
    primary_driver: str = Field(..., description="Identified primary driver of the problem/change")
    operational_bottleneck: str = Field(..., description="Bottleneck highlighted (e.g. 'last_mile_logistics', 'customer_support')")
    severity: str = Field(..., description="Severity level: 'low', 'medium', 'high', 'critical'")
    qualitative_assessment: str = Field(..., description="Brief qualitative overview of operational impacts")

class InsightResponse(AgentResponseBase):
    output: InsightOutput

# Impact Agent Output
class ImpactOutput(BaseModel):
    affected_skus: int = Field(..., description="Number of unique products/SKUs impacted")
    affected_daily_orders: int = Field(..., description="Number of daily orders projected to be impacted")
    projected_daily_loss_pkr: float = Field(..., description="Calculated financial loss or cost increase in PKR")
    margin_compression_pct: float = Field(..., description="Expected percentage drop in operating margins")

class ImpactResponse(AgentResponseBase):
    output: ImpactOutput

# Action Agent Output
class BusinessAction(BaseModel):
    rank: int = Field(..., description="Ranking of the action (1 to 3)")
    action_id: str = Field(..., description="Unique machine-readable ID for the action")
    description: str = Field(..., description="Detailed description of the proposed action")
    recovery_potential_pkr: float = Field(..., description="Estimated recovery value in PKR")
    tradeoff: str = Field(..., description="Known operational risk or drawback of this action")
    system_update: Dict[str, Any] = Field(..., description="Structured update command representing changes to state")

class ActionResponse(AgentResponseBase):
    output: List[BusinessAction]

# Execution Agent Output
class DiffItem(BaseModel):
    op: str = Field(..., description="Operation type: 'add', 'replace', or 'remove'")
    path: str = Field(..., description="JSON-path format of modified field, e.g. '/pricing_rules/base_delivery_fee'")
    value: Any = Field(None, description="New value applied")
    old_value: Optional[Any] = Field(None, description="Value before modification")

class ExecutionOutput(BaseModel):
    action_taken: str = Field(..., description="Action ID applied")
    before_state: Dict[str, Any] = Field(..., description="Snapshot of database state before mutation")
    after_state: Dict[str, Any] = Field(..., description="Snapshot of database state after mutation")
    diff: List[DiffItem] = Field(..., description="List of specific changes applied to mock_db.json")
    log_entry_id: str = Field(..., description="Generated UUID of the audit log entry")

class ExecutionResponse(AgentResponseBase):
    output: ExecutionOutput

# Master Pipeline Response
class PipelineResponse(BaseModel):
    request_id: str = Field(..., description="Unique identifier for this analysis run")
    input_text: str = Field(..., description="The raw input text processed")
    orchestrator: OrchestratorResponse
    ingestion: Optional[IngestionResponse] = None
    insight: Optional[InsightResponse] = None
    impact: Optional[ImpactResponse] = None
    actions: Optional[ActionResponse] = None
    execution: Optional[ExecutionResponse] = None
    agent_trace: List[Dict[str, Any]] = Field(..., description="Chronological log of agent durations")
    total_duration_ms: int = Field(..., description="Total execution time of the pipeline")
```

---

## 5. Detailed Dry-Run of Scenarios

### Scenario A: Nationwide Fuel Price Hike

```
Input Document:
"The Government of Pakistan announced today a 15% increase in fuel prices effective Monday. Petrol will rise from Rs. 280 to Rs. 322 per liter. Diesel from Rs. 290 to Rs. 333. The increase is attributed to global oil market pressures."
```

#### Step 1: Orchestrator Agent
* **Evaluation**: Inspects input. Notes keywords: "Government of Pakistan", "fuel prices", "Petrol", "Diesel".
* **Routing**: Relevant to logistics. Triggers the pipeline.
* **Output**:
  ```json
  {
    "should_halt": false,
    "reason": "National fuel price changes impact logistics and shipping costs; proceeding with full analysis.",
    "agents_invoked": ["ingestion", "insight", "impact", "actions", "execution"]
  }
  ```

#### Step 2: Ingestion Agent
* **Extraction**: Extracts variables.
* **Output**:
  ```json
  {
    "event_type": "fuel_price_hike",
    "magnitude_pct": 15.0,
    "effective_date": "Monday",
    "scope": "nationwide",
    "details": {
      "petrol_pkr_old": 280.0,
      "petrol_pkr_new": 322.0,
      "diesel_pkr_old": 290.0,
      "diesel_pkr_new": 333.0
    }
  }
  ```

#### Step 3: Insight Agent
* **Analysis**: Assesses how this translates to operations. Since third-party couriers charge fuel surcharges, cost per order rises.
* **Output**:
  ```json
  {
    "primary_driver": "delivery_costs",
    "operational_bottleneck": "last_mile_logistics",
    "severity": "high",
    "qualitative_assessment": "Nationwide diesel spike immediately increases delivery partner courier rates. Average fulfillment costs will rise, impacting lower-tier baskets."
  }
  ```

#### Step 4: Impact Agent
* **Context**: Reads current DB state. Identifies that there are 234 active SKUs, 1,200 daily orders, average ticket is Rs. 1,100, and standard delivery is Rs. 150.
* **Calculation**:
  - Courier surcharge = +Rs. 37.5 per shipment (based on ~12% logistics cost spike).
  - Total daily loss = 1,200 orders * Rs. 37.5 = Rs. 45,000.
  - Margin drop = 6.0%.
* **Output**:
  ```json
  {
    "affected_skus": 234,
    "affected_daily_orders": 1200,
    "projected_daily_loss_pkr": 45000.0,
    "margin_compression_pct": 6.0
  }
  ```

#### Step 5: Action Agent
* **Formulation**: Formulates responses based on `mock_db.json`. It notices many orders are below Rs. 800. Proposes dynamic delivery fees.
* **Output**:
  ```json
  [
    {
      "rank": 1,
      "action_id": "apply_delivery_surcharge",
      "description": "Add Rs. 50 delivery surcharge below Rs. 800 order value",
      "recovery_potential_pkr": 60000.0,
      "tradeoff": "Slight risk of conversion drop on low-value orders",
      "system_update": {
        "table": "pricing_rules",
        "field": "delivery_surcharges",
        "value": { "threshold_pkr": 800, "fee_pkr": 50 }
      }
    },
    {
      "rank": 2,
      "action_id": "increase_free_delivery_threshold",
      "description": "Increase free delivery threshold from Rs. 1500 to Rs. 2000",
      "recovery_potential_pkr": 30000.0,
      "tradeoff": "Reduces basket sizes in rural regions",
      "system_update": {
        "table": "pricing_rules",
        "field": "free_delivery_threshold",
        "value": 2000
      }
    },
    {
      "rank": 3,
      "action_id": "suspend_low_margin_skus",
      "description": "Deactivate 12 low-margin bulky items highly exposed to volumetric shipping charges",
      "recovery_potential_pkr": 10000.0,
      "tradeoff": "Reduces overall product catalog choice",
      "system_update": {
        "table": "pricing_rules",
        "field": "disabled_skus",
        "value": ["sku-vol-98", "sku-vol-122"]
      }
    }
  ]
  ```

#### Step 6: Execution Agent
* **Execution**: Reads `mock_db.json`. Parses the `system_update` of Rank 1 action.
* **Mutation**: Appends `{ "threshold_pkr": 800, "fee_pkr": 50 }` to `pricing_rules.delivery_surcharges`.
* **Output**:
  - Snapshot of before/after.
  - JSON diff: `[{ "op": "add", "path": "/pricing_rules/delivery_surcharges/0", "value": { "threshold_pkr": 800, "fee_pkr": 50 } }]`.
  - Appends to `action_log.json`.

---

### Scenario B: Lahore Order Volume Drop

```
Input Document:
"Internal sales report — Week 21: Lahore region orders dropped 25% week-over-week (from 4,800 to 3,600). Karachi and Islamabad steady. Customer service tickets in Lahore up 40%. No marketing changes were made."
```

#### Step 1: Orchestrator Agent
* **Evaluation**: Sales and customer service ticket anomalies in major hub (Lahore).
* **Routing**: Relevant to regional operations. Triggers full pipeline.
* **Output**:
  ```json
  {
    "should_halt": false,
    "reason": "Significant regional order volume decline (25%) coupled with customer service escalations requires immediate intervention.",
    "agents_invoked": ["ingestion", "insight", "impact", "actions", "execution"]
  }
  ```

#### Step 2: Ingestion Agent
* **Extraction**: Extracts variables.
* **Output**:
  ```json
  {
    "event_type": "order_decline",
    "magnitude_pct": 25.0,
    "effective_date": "Week 21",
    "scope": "Lahore",
    "details": {
      "orders_old_weekly": 4800,
      "orders_new_weekly": 3600,
      "ticket_increase_pct": 40.0
    }
  }
  ```

#### Step 3: Insight Agent
* **Analysis**: Correlates ticket spike and order drop. Since marketing is unchanged, it must be a delivery operations, logistics partner, or software bug issue in the Lahore area.
* **Output**:
  ```json
  {
    "primary_driver": "customer_satisfaction_issues",
    "operational_bottleneck": "customer_support_or_last_mile",
    "severity": "high",
    "qualitative_assessment": "Drop is Lahore-specific. The simultaneous 40% ticket increase confirms a service delivery failure rather than a market demand drop."
  }
  ```

#### Step 4: Impact Agent
* **Context**: Reads database. Identifies revenue loss.
* **Calculation**:
  - Weekly loss = 1,200 orders * average ticket size of Rs. 1,000 = Rs. 1,200,000.
  - Churn risk = High for Lahore customers.
* **Output**:
  ```json
  {
    "affected_skus": 0,
    "affected_daily_orders": 171,
    "projected_daily_loss_pkr": 171000.0,
    "margin_compression_pct": 12.0
  }
  ```

#### Step 5: Action Agent
* **Formulation**: Formulates campaign recovery options.
* **Output**:
  ```json
  [
    {
      "rank": 1,
      "action_id": "create_lahore_discount_campaign",
      "description": "Launch Lahore-only 15% discount campaign (recover ~70% of lost orders)",
      "recovery_potential_pkr": 840000.0,
      "tradeoff": "Short term margin impact on Lahore sales",
      "system_update": {
        "table": "campaigns",
        "field": "new_campaign",
        "value": {
          "campaign_id": "lh_recovery_15",
          "name": "Lahore Recovery Discount",
          "region": "Lahore",
          "discount_pct": 15.0,
          "active": true
        }
      }
    },
    {
      "rank": 2,
      "action_id": "escalate_cs_channels",
      "description": "Reallocate 4 support agents to dedicated Lahore ticket queue",
      "recovery_potential_pkr": 150000.0,
      "tradeoff": "Increases average wait time in Karachi and Islamabad queues",
      "system_update": {
        "table": "campaigns",
        "field": "cs_routing",
        "value": "priority_lahore"
      }
    },
    {
      "rank": 3,
      "action_id": "pause_lahore_marketing",
      "description": "Pause active Lahore acquisition marketing campaigns until service level returns to normal",
      "recovery_potential_pkr": 50000.0,
      "tradeoff": "Reduces inbound lead volume",
      "system_update": {
        "table": "campaigns",
        "field": "pause_marketing_region",
        "value": "Lahore"
      }
    }
  ]
  ```

#### Step 6: Execution Agent
* **Execution**: Reads `mock_db.json`. Parses the `system_update` of Rank 1 action.
* **Mutation**: Appends the new campaign object to `campaigns` array in `mock_db.json`.
* **Output**:
  - Snapshot of before/after.
  - JSON diff details.
  - Appends audit entry to `action_log.json`.

---

## 6. Tech Stack Decisions & Tradeoffs

The development environment is configured with strict software version specifications to ensure local builds match production runtime environments.

### A. Backend stack
* **Python 3.12**: Native support for dataclasses and Pydantic models.
* **FastAPI**: Core framework. Uses Starlette under the hood. Provides automatic OpenAPI docs (at `/docs`) which aids API verification.
* **Uvicorn**: Lightweight ASGI web server.
* **google-generativeai**: SDK to interact with Google Gemini models. We target `gemini-2.5-flash` due to its high speed and structural reliability.

### B. Mobile Stack
* **Flutter (v3.22.x or later)**: Framework for building native applications from a single codebase.
* **Dart**: Strongly typed programming language.
* **http**: Simple, reliable package for API networking.
* **provider** or **setState**: Simple state management appropriate for a hackathon. We will use a clean ChangeNotifier service paradigm to separate UI logic from API networking.

### C. Deployment & Hosting
* **Backend**: Render.com Free Instance.
* **Database**: Disk JSON file (`mock_db.json`). Safe and fully inspectable on the Render file system or local disk.
* **Local Proxy Tunnel**: ngrok. This is crucial for local testing, bridging the host backend (`localhost:8000`) with physical Android test phones connected via USB.

---

## 7. Mobile App Screen Flow & Wireframes

The app's design system uses a curated, premium dark mode layout inspired by modern dashboard designs.

### Color Palette
* **Background**: Deep Slate (`#0B0F17`)
* **Card Background**: Glassmorphic dark gray (`#151F32`) with thin border (`#2A3C5A`)
* **Primary Accent**: Electric Blue (`#3B82F6`)
* **Success Green**: Emerald (`#10B981`)
* **Warning Yellow**: Amber (`#F59E0B`)
* **Error Red**: Rose (`#F43F5E`)

### Screen Wireframes

#### Screen 1: Home Dashboard Screen
```
+-------------------------------------------------+
| [=] POLICYPULSE                      [Health OK] |
+-------------------------------------------------+
|  AUTONOMOUS CONTENT-TO-ACTION PIPELINE          |
|                                                 |
|  Select Hackathon Demo Scenario:                |
|  +-------------------------------------------+  |
|  | [ Scenario A: Fuel Price Hike (15%) ]     |  |
|  | [ Scenario B: Lahore Sales Drop (-25%) ]  |  |
|  +-------------------------------------------+  |
|                                                 |
|  Or Input Custom Article/Report:                |
|  +-------------------------------------------+  |
|  | Enter text here...                        |  |
|  |                                           |  |
|  +-------------------------------------------+  |
|                                                 |
|  [ >> TRIGGER AGENT PIPELINE << ]               |
|                                                 |
|  Quick Options:                                 |
|  [ View Database State ]   [ View Audit Trail ] |
|  [ Reset Database State ]                       |
+-------------------------------------------------+
```

#### Screen 2: Real-time Thinking Screen
Uses a custom vertical stepper layout. Finished steps display details in an expandable panel.
```
+-------------------------------------------------+
| <-- PIPELINE EXECUTION ENGINE                   |
+-------------------------------------------------+
|  Input: "Government of Pakistan announced..."  |
|  Status: PROCESSING (Elapsed: 2.4s)             |
|                                                 |
|  [o] ORCHESTRATOR AGENT                 [100%]  |
|      "Determined document is operational.       |
|       Triggering 5 specialists."                |
|                                                 |
|  [o] INGESTION AGENT                     [95%]  |
|      "Parsed: Fuel Hike, magnitude 15%,         |
|       effective Monday."                        |
|                                                 |
|  [>] INSIGHT AGENT (Thinking...)                |
|      "Analyzing delivery costs margin..."       |
|                                                 |
|  [ ] IMPACT AGENT                        [ - ]  |
|  [ ] ACTION AGENT                        [ - ]  |
|  [ ] EXECUTION AGENT                     [ - ]  |
|                                                 |
|  +-------------------------------------------+  |
|  | STREAMING LOGS                            |  |
|  | [Insight] query: 'fuel hike delivery cost'|  |
|  +-------------------------------------------+  |
+-------------------------------------------------+
```

#### Screen 3: Results & Database Diff Screen
Displays the executed action, the structural database diff, and summary information.
```
+-------------------------------------------------+
| <-- PIPELINE COMPLETED                          |
+-------------------------------------------------+
|  EXECUTED ACTION:                               |
|  "Apply Rs. 50 Delivery Surcharge"              |
|  Confidence: 99% | Latency: 2.8s                |
|                                                 |
|  Operational Reasoning:                         |
|  "Compensates for 12% rise in courier rates by  |
|   applying Rs.50 fee specifically below critical|
|   basket sizes of Rs. 800."                     |
|                                                 |
|  DATABASE STATE CHANGES:                        |
|  +-------------------------------------------+  |
|  | FIELD             | BEFORE    | AFTER     |  |
|  | surcharges        | []        | [Rs. 50]  |  |
|  | free_threshold    | 1500      | 1500      |  |
|  +-------------------------------------------+  |
|                                                 |
|  [ VIEW FULL JSON DIFF ]                        |
|  [ RESET SYSTEM STATE ]                         |
+-------------------------------------------------+
```

---

## 8. Mock Database Schema Details

The database will be instantiated as `backend/mock_db.json`. Below is the default mock structure containing both operational configurations and active customer segments:

```json
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
```

When reset, the backend will restore this exact document state.

---

## 9. Antigravity Orchestration Strategy

Antigravity controls the codebase layout and planning. Below is the detailed structure of the project which will be created under `C:\Users\BiM\.gemini\antigravity\scratch\policypulse`:

```
policypulse/
├── backend/
│   ├── main.py                       # FastAPI application, routing, endpoints, static mounts
│   ├── requirements.txt              # python dependency definitions
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
│   ├── pubspec.yaml                  # Flutter package definition (http, etc.)
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
    ├── implementation_plan.md        # This detailed plan
    ├── agent-system-prompts.md       # Verbatim LLM prompt architectures
    ├── task.md                       # Task checklist containing acceptance criteria
    ├── claude-code-prompts.md        # Explicit instruction prompts for Claude terminal calls
    ├── walkthrough.md                # Post-mortem and verification walkthrough
    └── claude-code-sessions/         # Log storage for Claude CLI transcripts
```

*Note: Since the user has no active workspace, Antigravity creates this structure in `C:\Users\BiM\.gemini\antigravity\scratch\policypulse` and recommends the user load this path as the active editor workspace.*

---

## 10. Risk Register & Mitigations

### A. Gemini API Rate Limiting or Outage
* **Risk**: The multi-agent pipeline makes 6 sequential API calls. A rate limit error during a demo would halt the app.
* **Mitigation**: 
  - Implementation of exponential backoff retry in `gemini_client.py` using `tenacity` or basic loops.
  - Setting a temperature of `0.1` to ensure structured JSON output consistency, reducing formatting errors that require retries.

### B. Incorrect JSON formatting from LLM
* **Risk**: Models sometimes wrap JSON in markdown tags (```json) or add introductory text, breaking Python's standard `json.loads`.
* **Mitigation**:
  - Utilizing Pydantic models with schema guidelines in prompts.
  - Implement a fallback parser regex pattern `\{.*?\}` (non-greedy) to extract pure JSON block from raw model output text before parsing.

### C. Physical Test Device Routing to Local Host
* **Risk**: A physical Android device connected via USB cannot resolve `localhost:8000` directly.
* **Mitigation**:
  - Expose backend using `ngrok http 8000` to generate a public HTTPS tunnel.
  - The mobile app's `lib/config.dart` must hold a configurable base URL so the user can easily swap local addresses with the active ngrok tunnel address.

### D. File Concurrency Issues
* **Risk**: Multiple API calls modifying `mock_db.json` simultaneously could lead to file corruption.
* **Mitigation**:
  - Wrap database read/write routines in a critical section lock using an `asyncio.Lock` in the FastAPI router to serialize access.

---

## 11. Code Style & Standards

### Python (Backend)
* **Formatting**: PEP 8 style formatting.
* **Typing**: Use static type annotations on all function signatures (`def run_agent(self, data: IngestionOutput) -> InsightResponse:`).
* **Logging**: Set up Python's standard `logging` library instead of writing raw `print` statements, printing structured timestamps to stdout.

### Dart (Flutter)
* **Structure**: Modular layout separating views (Screens) from controllers (Services).
* **Styling**: All widgets must inherit colors and text themes from the central `theme.dart` (no hardcoded colors like `Colors.blue` scattered inside layout trees).
* **Linting**: Ensure `flutter analyze` runs clean without warnings.

---

## 12. Verification and Testing Strategy

We will use a multi-tiered verification plan to ensure the project works perfectly before final packaging:

### Phase 1: API Level Tests
* Trigger API endpoints using standard cURL commands:
  ```bash
  curl -X GET http://localhost:8000/health
  curl -X POST http://localhost:8000/reset
  ```
* Validate structure of `/state` and `/analyze` responses.

### Phase 2: Agent Level Tests
* Run a dry run script `python test_agents.py` locally that executes Scenario A and Scenario B and checks that `mock_db.json` is modified correctly and the output conforms to expectations.

### Phase 3: Mobile Layout Integration
* Compile Flutter project in debug mode:
  ```bash
  flutter run
  ```
* Test on physical phone via USB. Confirm endpoints execute and state diff renders dynamically.
* Confirm that clicking the "Reset Database" button successfully issues a POST to `/reset` and refreshes the Dashboard.
* Compile and build final Android Application Package:
  ```bash
  flutter build apk --release
  ```
* Confirm that the compiled output `app-release.apk` is generated under `build/app/outputs/flutter-apk/app-release.apk`.

// Hand-written models for the /analyze response. No codegen.
// All fromJson constructors are defensive: missing/optional fields
// degrade to null or empty collections rather than throwing.

class AgentResponse {
  final dynamic output;
  final double confidence;
  final String reasoning;
  final String agentName;
  final String timestamp;

  AgentResponse({
    this.output,
    this.confidence = 0.0,
    this.reasoning = '',
    this.agentName = '',
    this.timestamp = '',
  });

  factory AgentResponse.fromJson(Map<String, dynamic> json) {
    return AgentResponse(
      output: json['output'],
      confidence: (json['confidence'] as num?)?.toDouble() ?? 0.0,
      reasoning: json['reasoning']?.toString() ?? '',
      agentName: json['agent_name']?.toString() ?? '',
      timestamp: json['timestamp']?.toString() ?? '',
    );
  }
}

class ActionItem {
  final int rank;
  final String action;
  final String expectedImpact;
  final String rationale;

  ActionItem({
    this.rank = 0,
    this.action = '',
    this.expectedImpact = '',
    this.rationale = '',
  });

  factory ActionItem.fromJson(Map<String, dynamic> json) {
    return ActionItem(
      rank: (json['rank'] as num?)?.toInt() ?? 0,
      action: json['action']?.toString() ?? '',
      expectedImpact: json['expected_impact']?.toString() ?? '',
      rationale: json['rationale']?.toString() ?? '',
    );
  }
}

class DiffEntry {
  final String path;
  final dynamic oldValue;
  final dynamic newValue;

  DiffEntry({
    this.path = '',
    this.oldValue,
    this.newValue,
  });

  factory DiffEntry.fromJson(Map<String, dynamic> json) {
    return DiffEntry(
      path: json['path']?.toString() ?? '',
      oldValue: json['old'],
      newValue: json['new'],
    );
  }
}

class PipelineResponse {
  final String requestId;
  final int totalDurationMs;
  final String inputText;
  final AgentResponse? orchestrator;
  final AgentResponse? ingestion;
  final AgentResponse? insight;
  final AgentResponse? impact;
  final AgentResponse? actions;
  final AgentResponse? execution;
  final List<AgentResponse> agentTrace;
  final List<DiffEntry> executionDiff;
  final String? actionTaken;
  final List<ActionItem> actionItems;

  PipelineResponse({
    this.requestId = '',
    this.totalDurationMs = 0,
    this.inputText = '',
    this.orchestrator,
    this.ingestion,
    this.insight,
    this.impact,
    this.actions,
    this.execution,
    this.agentTrace = const [],
    this.executionDiff = const [],
    this.actionTaken,
    this.actionItems = const [],
  });

  static AgentResponse? _agent(dynamic value) {
    if (value is Map<String, dynamic>) {
      return AgentResponse.fromJson(value);
    }
    return null;
  }

  factory PipelineResponse.fromJson(Map<String, dynamic> json) {
    final actions = _agent(json['actions']);
    final execution = _agent(json['execution']);

    // Extract action items from actions.output.actions.
    final actionItems = <ActionItem>[];
    final actionsOutput = actions?.output;
    if (actionsOutput is Map<String, dynamic>) {
      final rawActions = actionsOutput['actions'];
      if (rawActions is List) {
        for (final item in rawActions) {
          if (item is Map<String, dynamic>) {
            actionItems.add(ActionItem.fromJson(item));
          }
        }
      }
    }

    // Extract diff entries and action_taken from execution.output.
    final executionDiff = <DiffEntry>[];
    String? actionTaken;
    final executionOutput = execution?.output;
    if (executionOutput is Map<String, dynamic>) {
      actionTaken = executionOutput['action_taken']?.toString();
      final rawDiff = executionOutput['diff'];
      if (rawDiff is List) {
        for (final item in rawDiff) {
          if (item is Map<String, dynamic>) {
            executionDiff.add(DiffEntry.fromJson(item));
          }
        }
      }
    }

    // Extract the ordered agent trace.
    final agentTrace = <AgentResponse>[];
    final rawTrace = json['agent_trace'];
    if (rawTrace is List) {
      for (final item in rawTrace) {
        if (item is Map<String, dynamic>) {
          agentTrace.add(AgentResponse.fromJson(item));
        }
      }
    }

    return PipelineResponse(
      requestId: json['request_id']?.toString() ?? '',
      totalDurationMs: (json['total_duration_ms'] as num?)?.toInt() ?? 0,
      inputText: json['input_text']?.toString() ?? '',
      orchestrator: _agent(json['orchestrator']),
      ingestion: _agent(json['ingestion']),
      insight: _agent(json['insight']),
      impact: _agent(json['impact']),
      actions: actions,
      execution: execution,
      agentTrace: agentTrace,
      executionDiff: executionDiff,
      actionTaken: actionTaken,
      actionItems: actionItems,
    );
  }
}

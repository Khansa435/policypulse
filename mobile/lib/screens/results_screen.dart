import 'package:flutter/material.dart';

import '../models/pipeline_response.dart';

const _accent = Color(0xFF7DD3FC); // sky
const _green = Color(0xFF34D399); // emerald-400
const _red = Color(0xFFF87171); // red-400
const _amber = Color(0xFFFBBF24); // amber-400
const _cardBg = Color(0xFF161B26);

class ResultsScreen extends StatefulWidget {
  final PipelineResponse response;
  const ResultsScreen({super.key, required this.response});

  @override
  State<ResultsScreen> createState() => _ResultsScreenState();
}

class _ResultsScreenState extends State<ResultsScreen> {
  final Set<int> _expandedIndices = {};
  bool _showPipeline = false;

  PipelineResponse get response => widget.response;

  @override
  Widget build(BuildContext context) {
    final isHalted = response.agentTrace.length <= 1 &&
        response.executionDiff.isEmpty &&
        response.actionItems.isEmpty;

    final children = <Widget>[];

    if (isHalted) {
      children.add(_haltedCard());
    } else {
      final actionTaken = response.actionTaken;
      if (actionTaken != null && actionTaken.isNotEmpty) {
        children.add(_actionPill(actionTaken));
      }
      if (response.actionItems.isNotEmpty) {
        if (children.isNotEmpty) children.add(const SizedBox(height: 16));
        children.add(_actionsCard());
      }
      if (response.executionDiff.isNotEmpty) {
        if (children.isNotEmpty) children.add(const SizedBox(height: 16));
        children.add(_diffCard());
      }
      if (children.isNotEmpty) children.add(const SizedBox(height: 16));
      children.add(_pipelineSection());
    }

    return Scaffold(
      appBar: AppBar(
        title: const Text('Recommended Actions'),
        centerTitle: true,
        elevation: 0,
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: children,
        ),
      ),
    );
  }

  // --- Shared card decoration ------------------------------------------------

  BoxDecoration get _cardDecoration => BoxDecoration(
        color: _cardBg,
        borderRadius: BorderRadius.circular(12),
      );

  // --- Action taken pill -----------------------------------------------------

  Widget _actionPill(String actionTaken) {
    return Container(
      padding: const EdgeInsets.symmetric(vertical: 8, horizontal: 12),
      decoration: BoxDecoration(
        color: _green.withValues(alpha: 0.15),
        borderRadius: BorderRadius.circular(8),
      ),
      child: Row(
        children: [
          const Icon(Icons.check_circle_outline, color: _green, size: 18),
          const SizedBox(width: 8),
          Expanded(
            child: Text(
              'Action taken: $actionTaken',
              style: const TextStyle(
                color: _green,
                fontWeight: FontWeight.bold,
              ),
            ),
          ),
        ],
      ),
    );
  }

  // --- Halt edge case --------------------------------------------------------

  Widget _haltedCard() {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: _cardDecoration,
      child: const Row(
        children: [
          Icon(Icons.info_outline, color: _amber),
          SizedBox(width: 12),
          Expanded(
            child: Text(
              'Document was classified as not business-relevant. The pipeline '
              'was halted by the orchestrator.',
            ),
          ),
        ],
      ),
    );
  }

  // --- Collapsible pipeline section ------------------------------------------

  Widget _pipelineSection() {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: _cardDecoration,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          InkWell(
            onTap: () => setState(() => _showPipeline = !_showPipeline),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Row(
                      children: [
                        const Icon(Icons.settings, size: 18, color: _accent),
                        const SizedBox(width: 8),
                        const Text(
                          'Show how this was generated',
                          style: TextStyle(
                            fontSize: 14,
                            color: _accent,
                            fontWeight: FontWeight.w500,
                          ),
                        ),
                      ],
                    ),
                    Icon(
                      _showPipeline ? Icons.expand_less : Icons.expand_more,
                      color: _accent,
                    ),
                  ],
                ),
                const SizedBox(height: 4),
                Text(
                  'View 6-agent pipeline trace',
                  style: TextStyle(
                    fontSize: 11,
                    color: Colors.white.withValues(alpha: 0.5),
                  ),
                ),
              ],
            ),
          ),
          if (_showPipeline) ...[
            const SizedBox(height: 12),
            Text(
              'Tap any agent to view its full reasoning',
              style: TextStyle(
                fontSize: 11,
                color: Colors.white.withValues(alpha: 0.5),
              ),
            ),
            const SizedBox(height: 12),
            for (int i = 0; i < response.agentTrace.length; i++)
              _agentRow(i, response.agentTrace[i]),
          ],
        ],
      ),
    );
  }

  Widget _agentRow(int index, AgentResponse agent) {
    final name = agent.agentName.isNotEmpty
        ? agent.agentName[0].toUpperCase() + agent.agentName.substring(1)
        : agent.agentName;
    final isExpanded = _expandedIndices.contains(index);
    final isLast = index == response.agentTrace.length - 1;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        InkWell(
          onTap: () {
            setState(() {
              if (isExpanded) {
                _expandedIndices.remove(index);
              } else {
                _expandedIndices.add(index);
              }
            });
          },
          child: Padding(
            padding: const EdgeInsets.symmetric(vertical: 8),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Text(name, style: const TextStyle(fontSize: 14)),
                    Row(
                      children: [
                        _ConfidenceBadge(value: agent.confidence),
                        const SizedBox(width: 6),
                        Icon(
                          isExpanded
                              ? Icons.expand_less
                              : Icons.expand_more,
                          size: 18,
                          color: Colors.white.withValues(alpha: 0.5),
                        ),
                      ],
                    ),
                  ],
                ),
                AnimatedSize(
                  duration: const Duration(milliseconds: 150),
                  alignment: Alignment.topCenter,
                  child: isExpanded
                      ? Padding(
                          padding: const EdgeInsets.only(top: 8),
                          child: Text(
                            agent.reasoning,
                            style: TextStyle(
                              fontSize: 12,
                              color: Colors.white.withValues(alpha: 0.7),
                            ),
                          ),
                        )
                      : const SizedBox(width: double.infinity),
                ),
              ],
            ),
          ),
        ),
        if (!isLast)
          Divider(height: 1, color: Colors.white.withValues(alpha: 0.08)),
      ],
    );
  }

  // --- Section 3: ranked actions ---------------------------------------------

  Widget _actionsCard() {
    final items = [...response.actionItems]
      ..sort((a, b) => a.rank.compareTo(b.rank));

    return Container(
      padding: const EdgeInsets.all(16),
      decoration: _cardDecoration,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text(
            'Ranked Actions',
            style: TextStyle(fontWeight: FontWeight.bold, fontSize: 16),
          ),
          const SizedBox(height: 12),
          for (final item in items) _actionItem(item),
        ],
      ),
    );
  }

  Widget _actionItem(ActionItem item) {
    return Container(
      margin: const EdgeInsets.only(bottom: 12),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 4),
            decoration: BoxDecoration(
              color: _accent.withValues(alpha: 0.2),
              borderRadius: BorderRadius.circular(6),
            ),
            child: Text(
              '#${item.rank}',
              style: const TextStyle(
                color: _accent,
                fontWeight: FontWeight.bold,
                fontSize: 12,
              ),
            ),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  item.action,
                  style: const TextStyle(
                    fontWeight: FontWeight.bold,
                    fontSize: 14,
                  ),
                ),
                const SizedBox(height: 4),
                Text(
                  'Expected: ${item.expectedImpact}',
                  style: const TextStyle(fontSize: 12, color: _accent),
                ),
                const SizedBox(height: 4),
                Text(
                  'Why: ${item.rationale}',
                  style: TextStyle(
                    fontSize: 12,
                    color: Colors.white.withValues(alpha: 0.6),
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  // --- Section 4: state mutation diff ----------------------------------------

  Widget _diffCard() {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: _cardDecoration,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text(
            'Database changes',
            style: TextStyle(fontWeight: FontWeight.bold, fontSize: 16),
          ),
          const SizedBox(height: 2),
          Text(
            'These changes were persisted to disk',
            style: TextStyle(
              fontSize: 11,
              color: Colors.white.withValues(alpha: 0.5),
            ),
          ),
          const SizedBox(height: 12),
          for (final entry in response.executionDiff) _diffRow(entry),
        ],
      ),
    );
  }

  Widget _diffRow(DiffEntry entry) {
    return Container(
      margin: const EdgeInsets.only(bottom: 8),
      padding: const EdgeInsets.all(10),
      decoration: BoxDecoration(
        color: const Color(0xFF0B0F17),
        borderRadius: BorderRadius.circular(8),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            entry.path,
            style: const TextStyle(
              fontFamily: 'monospace',
              fontSize: 12,
              color: _accent,
            ),
          ),
          const SizedBox(height: 6),
          Row(
            children: [
              Text(
                '${entry.oldValue ?? '—'}',
                style: const TextStyle(
                  color: _red,
                  decoration: TextDecoration.lineThrough,
                  fontSize: 12,
                  fontFamily: 'monospace',
                ),
              ),
              const SizedBox(width: 8),
              Icon(
                Icons.arrow_forward,
                size: 14,
                color: Colors.white.withValues(alpha: 0.5),
              ),
              const SizedBox(width: 8),
              Expanded(
                child: Text(
                  '${entry.newValue ?? '—'}',
                  style: const TextStyle(
                    color: _green,
                    fontSize: 12,
                    fontFamily: 'monospace',
                  ),
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }
}

class _ConfidenceBadge extends StatelessWidget {
  final double value;
  const _ConfidenceBadge({required this.value});

  @override
  Widget build(BuildContext context) {
    Color color;
    if (value >= 0.8) {
      color = _green;
    } else if (value >= 0.5) {
      color = _amber;
    } else {
      color = _red;
    }
    final pct = (value * 100).toStringAsFixed(0);
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.15),
        borderRadius: BorderRadius.circular(12),
      ),
      child: Text(
        '$pct%',
        style: TextStyle(
          color: color,
          fontSize: 12,
          fontWeight: FontWeight.bold,
        ),
      ),
    );
  }
}

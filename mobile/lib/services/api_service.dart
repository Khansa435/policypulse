import 'dart:convert';

import 'package:http/http.dart' as http;

import '../config.dart';
import '../models/pipeline_response.dart';

/// Thin client over the FastAPI backend.
class ApiService {
  /// Runs the full agent pipeline. Backend takes ~45s, so we allow 120s.
  Future<PipelineResponse> analyze(String text, {String? scenarioHint}) async {
    final uri = Uri.parse('$apiBaseUrl/analyze');

    final response = await http
        .post(
          uri,
          headers: {'Content-Type': 'application/json'},
          body: jsonEncode({
            'text': text,
            'scenario_hint': scenarioHint ?? 'policy',
          }),
        )
        .timeout(const Duration(seconds: 120));

    if (response.statusCode != 200) {
      throw Exception(
        'Analyze failed (${response.statusCode}): ${response.body}',
      );
    }

    final json = jsonDecode(response.body) as Map<String, dynamic>;
    return PipelineResponse.fromJson(json);
  }
}

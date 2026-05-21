// Basic smoke test for the PolicyPulse app shell.

import 'package:flutter_test/flutter_test.dart';

import 'package:policypulse/main.dart';

void main() {
  testWidgets('App renders the home screen', (WidgetTester tester) async {
    await tester.pumpWidget(const PolicyPulseApp());

    expect(find.text('PolicyPulse'), findsOneWidget);
    expect(
      find.text('Phase 3 in progress — tap to test backend'),
      findsOneWidget,
    );
  });
}

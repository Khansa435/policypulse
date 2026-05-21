import 'package:flutter/material.dart';

import 'screens/home_screen.dart';
import 'theme.dart';

void main() {
  runApp(const PolicyPulseApp());
}

class PolicyPulseApp extends StatelessWidget {
  const PolicyPulseApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'PolicyPulse',
      theme: appTheme(),
      home: const HomeScreen(),
    );
  }
}

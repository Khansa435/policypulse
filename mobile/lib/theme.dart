import 'package:flutter/material.dart';

const Color _scaffoldBg = Color(0xFF0B0F17);
const Color _cardBg = Color(0xFF161B26);
const Color _accent = Color(0xFF7DD3FC); // sky blue

/// Single dark theme for the whole app.
ThemeData appTheme() {
  final base = ThemeData.dark(useMaterial3: true);

  return base.copyWith(
    scaffoldBackgroundColor: _scaffoldBg,
    colorScheme: base.colorScheme.copyWith(
      primary: _accent,
      secondary: _accent,
      surface: _cardBg,
      onPrimary: Colors.black,
      onSurface: Colors.white,
    ),
    cardColor: _cardBg,
    cardTheme: const CardThemeData(color: _cardBg),
    appBarTheme: const AppBarTheme(
      backgroundColor: _scaffoldBg,
      foregroundColor: Colors.white,
      elevation: 0,
    ),
    textTheme: base.textTheme.apply(
      bodyColor: Colors.white,
      displayColor: Colors.white,
    ),
    elevatedButtonTheme: ElevatedButtonThemeData(
      style: ElevatedButton.styleFrom(
        backgroundColor: _accent,
        foregroundColor: Colors.black,
      ),
    ),
  );
}

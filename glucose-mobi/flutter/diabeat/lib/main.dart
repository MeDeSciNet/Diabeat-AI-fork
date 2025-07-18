import 'package:flutter/material.dart';
import 'package:dynamic_color/dynamic_color.dart';
import 'home_page.dart';

void main() {
  runApp(const MainApp());
}

class MainApp extends StatelessWidget {
  const MainApp({super.key});

  @override
  Widget build(context) => DynamicColorBuilder(
    builder: (lightDynamic, darkDynamic) {
      lightDynamic =
          lightDynamic?.harmonized() ??
          ColorScheme.fromSeed(
            seedColor: Colors.blue,
            brightness: Brightness.light,
          );

      darkDynamic =
          darkDynamic?.harmonized() ??
          ColorScheme.fromSeed(
            seedColor: Colors.blue,
            brightness: Brightness.dark,
          );

      return MaterialApp(
        home: const HomePage(),
        theme: ThemeData(useMaterial3: true, colorScheme: lightDynamic),
        darkTheme: ThemeData(useMaterial3: true, colorScheme: darkDynamic),
      );
    },
  );
}

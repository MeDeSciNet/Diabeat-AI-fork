import 'package:diabeat/network/connection.dart' as connection;
import 'package:diabeat/network/session.dart' as session;
import 'package:diabeat/routes/scanner/scanner.dart';
import 'package:diabeat/routes/guest/guest.dart';
import 'package:diabeat/routes/home/home.dart';
import 'package:flutter/material.dart';
import 'package:dynamic_color/dynamic_color.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  await connection.load();
  final existSession = await session.load();
  runApp(_MainApp(existSession));
}

class _MainApp extends StatelessWidget {
  const _MainApp(this._existSession);
  final bool _existSession;

  @override
  Widget build(BuildContext context) {
    return DynamicColorBuilder(
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
          initialRoute: _existSession ? '/home' : '/guest',
          routes: {
            '/home': (context) => const HomePage(),
            '/guest': (context) => const GuestPage(),
            '/scanner': (context) => const ScannerPage(),
          },
          theme: ThemeData(useMaterial3: true, colorScheme: lightDynamic),
          darkTheme: ThemeData(useMaterial3: true, colorScheme: darkDynamic),
        );
      },
    );
  }
}

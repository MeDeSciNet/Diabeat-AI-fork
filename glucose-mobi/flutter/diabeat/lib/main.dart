import 'package:diabeat/routes/guest/login.dart';
import 'package:diabeat/routes/guest/register.dart';
import 'package:diabeat/routes/network/connection.dart' as connection;
import 'package:diabeat/routes/network/session.dart' as session;
import 'package:diabeat/routes/network/scanner.dart';
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
            '/home': (context) => const Home(),
            '/guest': (context) => const GuestPage(),
            '/guest/login': (context) => const LoginPage(),
            '/guest/register': (context) => const RegisterPage(),
            '/scanner': (context) => ScannerPage(),
          },
          theme: ThemeData(useMaterial3: true, colorScheme: lightDynamic),
          darkTheme: ThemeData(useMaterial3: true, colorScheme: darkDynamic),
        );
      },
    );
  }
}

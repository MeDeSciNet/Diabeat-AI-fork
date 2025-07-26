import 'package:diabeat/routes/connection/request.dart';
import 'package:diabeat/routes/connection/scanner.dart';
import 'package:diabeat/routes/guest/guest.dart';
import 'package:diabeat/routes/guest/login.dart';
import 'package:diabeat/routes/guest/register.dart';
import 'package:diabeat/routes/home/home.dart';
import 'package:flutter/material.dart';
import 'package:dynamic_color/dynamic_color.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  await Request.init();
  runApp(const _MainApp());
}

class _MainApp extends StatelessWidget {
  const _MainApp();

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
          initialRoute: '/guest', // TODO
          routes: {
            '/guest': (context) => const GuestPage(),
            '/guest/login': (context) => const LoginPage(),
            '/guest/register': (context) => const RegisterPage(),
            '/home': (context) => const Home(),
            '/connection/scanner': (context) => ScannerPage(),
          },
          theme: ThemeData(useMaterial3: true, colorScheme: lightDynamic),
          darkTheme: ThemeData(useMaterial3: true, colorScheme: darkDynamic),
        );
      },
    );
  }
}

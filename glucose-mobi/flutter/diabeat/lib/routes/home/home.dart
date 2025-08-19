import 'package:diabeat/routes/home/account/account.dart';
import 'package:diabeat/routes/home/account/consult/consult.dart';
import 'package:diabeat/routes/home/account/predict_diabetes/predict_diabetes.dart';
import 'package:diabeat/routes/home/history/history.dart';
import 'package:diabeat/routes/home/record/record.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

class Home extends StatefulWidget {
  const Home({super.key});

  @override
  State<Home> createState() => _HomeState();
}

class _HomeState extends State<Home> {
  final _navigatorKeys = [
    GlobalKey<NavigatorState>(),
    GlobalKey<NavigatorState>(),
    GlobalKey<NavigatorState>(),
  ];
  final _recordKey = GlobalKey<RecordPageState>();
  final _historyKey = GlobalKey<HistoryPageState>();
  int _index = 0;

  @override
  Widget build(BuildContext context) {
    return PopScope(
      canPop: false,
      onPopInvokedWithResult: (didPop, result) {
        if (didPop) return;

        final navigator = _navigatorKeys[_index].currentState!;
        if (navigator.canPop()) {
          navigator.pop();
        } else if (_index != 0) {
          setState(() => _index = 0);
        } else {
          SystemNavigator.pop();
        }
      },
      child: Scaffold(
        body: IndexedStack(
          index: _index,
          children: [
            Navigator(
              key: _navigatorKeys[0],
              initialRoute: '/',
              onGenerateRoute: (settings) {
                return switch (settings.name) {
                  '/' => MaterialPageRoute(
                    builder: (context) => RecordPage(key: _recordKey),
                  ),
                  _ => null,
                };
              },
            ),
            Navigator(
              key: _navigatorKeys[1],
              initialRoute: '/',
              onGenerateRoute: (settings) {
                return switch (settings.name) {
                  '/' => MaterialPageRoute(
                    builder: (context) => HistoryPage(key: _historyKey),
                  ),
                  _ => null,
                };
              },
            ),
            Navigator(
              key: _navigatorKeys[2],
              initialRoute: '/',
              onGenerateRoute: (settings) {
                return switch (settings.name) {
                  '/' => MaterialPageRoute(
                    builder: (context) => const AccountPage(),
                  ),
                  '/predict' => MaterialPageRoute(
                    builder: (context) => const PredictDiabetesRoot(),
                  ),
                  '/consult' => MaterialPageRoute(
                    builder: (context) => const ConsultPage(),
                  ),
                  _ => null,
                };
              },
            ),
          ],
        ),
        bottomNavigationBar:NavigationBar(
          selectedIndex: _index,
          onDestinationSelected: (value) {
            // unfocus textfield of current navigator
            // prevent keyboard pop up when dismiss dialog
            _navigatorKeys[_index].currentState!.focusNode.unfocus();

            if (value == 1 && _recordKey.currentState!.shouldRefresh) {
              _recordKey.currentState!.shouldRefresh = false;
              _historyKey.currentState!.getRecords(goToToday: false);
            }
            setState(() => _index = value);
          },
          destinations: const [
            NavigationDestination(
              label: '紀錄',
              icon: Icon(Icons.create_outlined),
              selectedIcon: Icon(Icons.create_rounded),
            ),
            NavigationDestination(
              label: '歷史',
              icon: Icon(Icons.history_outlined),
              selectedIcon: Icon(Icons.history_rounded),
            ),
            NavigationDestination(
              label: '帳號',
              icon: Icon(Icons.account_circle_outlined),
              selectedIcon: Icon(Icons.account_circle_rounded),
            ),
          ],
        ),
      ),
    );
  }
}

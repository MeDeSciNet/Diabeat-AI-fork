import 'package:diabeat/routes/home/account/account.dart';
import 'package:diabeat/routes/home/history/history.dart';
import 'package:diabeat/routes/home/record/record.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

class HomePage extends StatefulWidget {
  const HomePage({super.key});

  @override
  State<HomePage> createState() => _HomePageState();
}

class _HomePageState extends State<HomePage> {
  final _recordKey = GlobalKey<RecordPageState>();
  final _historyKey = GlobalKey<HistoryPageState>();
  final _accountNavigatorKey = GlobalKey<NavigatorState>();
  int _index = 0;

  @override
  Widget build(BuildContext context) {
    return PopScope(
      canPop: false,
      onPopInvokedWithResult: (didPop, result) {
        if (didPop) return;

        final navigator = Navigator.of(
          switch (_index) {
            0 => _recordKey,
            1 => _historyKey,
            _ => _accountNavigatorKey,
          }.currentContext!,
        );

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
            RecordPage(key: _recordKey),
            HistoryPage(key: _historyKey),
            Navigator(
              key: _accountNavigatorKey,
              onGenerateRoute: (settings) {
                return MaterialPageRoute(
                  builder: (context) => const AccountPage(),
                );
              },
            ),
          ],
        ),
        bottomNavigationBar: NavigationBar(
          selectedIndex: _index,
          onDestinationSelected: (value) {
            primaryFocus?.unfocus();

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

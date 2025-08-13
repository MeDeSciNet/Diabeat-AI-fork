import 'dart:async';
import 'package:diabeat/routes/home/account/account.dart';
import 'package:diabeat/routes/home/account/chat/chat.dart';
import 'package:diabeat/routes/home/account/predict_diabetes/root.dart';
import 'package:diabeat/routes/home/chart/chart.dart';
import 'package:diabeat/routes/home/record/record.dart';
import 'package:diabeat/routes/network/dialog/refresh_failed_dialog.dart';
import 'package:diabeat/routes/network/dialog/timeout.dart';
import 'package:diabeat/routes/network/prefs.dart' as prefs;
import 'package:diabeat/routes/network/request.dart' as request;
import 'package:diabeat/routes/network/session.dart' as session;
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
  final _recordPageKey = GlobalKey<RecordPageState>();
  final _chartPageKey = GlobalKey<ChartPageState>();
  final _accountPageKey = GlobalKey<AccountPageState>();
  int _index = 0;

  Future<bool> _noSessionRefresh(BuildContext context) async {
    final oldRefreshToken = await prefs.readRefreshToken();
    while (true) {
      try {
        return context.mounted &&
            await request.refresh(context, oldRefreshToken);
        //
      } on TimeoutException {
        if (!context.mounted || await TimeoutDialog.show(context) == null) {
          if (context.mounted) {
            RefreshFailedDialog.show(context);
          }
          return false;
        }
      }
    }
  }

  @override
  void initState() {
    if (!session.loggedIn) {
      () async {
        if (await _noSessionRefresh(context)) {
          _recordPageKey.currentState!.update();
          _chartPageKey.currentState!.update();
          _accountPageKey.currentState!.update();
        }
      }();
    }
    super.initState();
  }

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
                    builder: (context) => RecordPage(key: _recordPageKey),
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
                    builder: (context) => ChartPage(key: _chartPageKey),
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
                    builder: (context) => AccountPage(key: _accountPageKey),
                  ),
                  '/predict' => MaterialPageRoute(
                    builder: (context) => PredictDiabetesRoot(),
                  ),
                  '/chat' => MaterialPageRoute(
                    builder: (context) => ChatPage(),
                  ),
                  _ => null,
                };
              },
            ),
          ],
        ),
        bottomNavigationBar: BottomNavigationBar(
          currentIndex: _index,
          onTap: (value) {
            setState(() => _index = value);
          },
          items: const [
            BottomNavigationBarItem(
              label: '紀錄',
              icon: Icon(Icons.create_outlined),
              activeIcon: Icon(Icons.create),
            ),
            BottomNavigationBarItem(
              label: '圖表',
              icon: Icon(Icons.insert_chart_outlined),
              activeIcon: Icon(Icons.insert_chart),
            ),
            BottomNavigationBarItem(
              label: '帳號',
              icon: Icon(Icons.account_circle_outlined),
              activeIcon: Icon(Icons.account_circle),
            ),
          ],
        ),
      ),
    );
  }
}

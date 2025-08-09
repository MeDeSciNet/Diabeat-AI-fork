import 'package:diabeat/routes/home/account/account.dart';
import 'package:diabeat/routes/home/chart/chart.dart';
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
              onGenerateRoute: (settings) {
                return MaterialPageRoute(
                  builder: (context) => const RecordPage(),
                );
              },
            ),
            Navigator(
              key: _navigatorKeys[1],
              onGenerateRoute: (settings) {
                return MaterialPageRoute(
                  builder: (context) => const ChartPage(),
                );
              },
            ),
            Navigator(
              key: _navigatorKeys[2],
              onGenerateRoute: (settings) {
                return MaterialPageRoute(
                  builder: (context) => const AccountPage(),
                );
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
              label: '其他',
              icon: Icon(Icons.widgets_outlined),
              activeIcon: Icon(Icons.widgets),
            ),
          ],
        ),
      ),
    );
  }
}

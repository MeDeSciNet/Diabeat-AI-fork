import 'package:flutter/material.dart';
import 'guest/guest.dart';
import 'record/record.dart';
import 'chart/chart.dart';
import 'account/account.dart';
import 'util.dart';

class Home extends StatefulWidget {
  const Home({super.key});

  @override
  State<Home> createState() => _HomeState();
}

class _HomeState extends State<Home> {
  int _index = -1; // guest page

  @override
  Widget build(_) => _index < 0
      ? const GuestPage()
      : PopScope(
          onPopInvokedWithResult: (didPop, _) {
            if (!didPop) {
              setState(() => _index = 0);
            }
          },
          child: Scaffold(
            body: IndexedStack(
              index: _index,
              children: [
                navigator((_) => const RecordPage()),
                navigator((_) => const ChartPage()),
                navigator((_) => const AccountPage()),
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

import 'package:diabeat/routes/home/account/account.dart';
import 'package:diabeat/routes/home/chart/chart.dart';
import 'package:diabeat/routes/home/record/record.dart';
import 'package:flutter/material.dart';

class Home extends StatefulWidget {
  const Home({super.key});

  @override
  State<Home> createState() => _HomeState();
}

class _HomeState extends State<Home> {
  int _index = 0;

  @override
  Widget build(BuildContext context) => PopScope(
    onPopInvokedWithResult: (didPop, result) {
      if (!didPop) {
        setState(() => _index = 0);
      }
    },
    child: Scaffold(
      body: IndexedStack(
        index: _index,
        children: [const RecordPage(), const ChartPage(), const AccountPage()],
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

import 'package:flutter/material.dart';
import 'welcome_page.dart';
import 'record_page.dart';
import 'chart_page.dart';
import 'account_page.dart';

class HomePage extends StatefulWidget {
  const HomePage({super.key});

  @override
  State<StatefulWidget> createState() => _HomePageState();
}

class _HomePageState extends State<HomePage> {
  var pageIndices = (-1, 0);

  final pages = [
    [const WelcomePage()],
    [const RecordPage()],
    [const ChartPage()],
    [const AccountPage()],
  ];

  @override
  Widget build(context) => Scaffold(
    body: SafeArea(child: pages[1 + pageIndices.$1][pageIndices.$2]),
    bottomNavigationBar: pageIndices.$1 >= 0
        ? BottomNavigationBar(
            currentIndex: pageIndices.$1,
            onTap: (value) {
              setState(() => pageIndices = (value, 0));
            },
            items: [
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
          )
        : null,
  );
}

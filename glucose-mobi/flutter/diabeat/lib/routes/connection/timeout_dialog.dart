import 'package:diabeat/nav.dart';
import 'package:diabeat/util.dart';
import 'package:flutter/material.dart';

enum TimeoutDialogNav { retry, _scan }

class TimeoutDialog extends StatelessWidget {
  const TimeoutDialog._();

  static Future<dynamic> show(BuildContext context) async {
    final nav = await showDialog(
      context: context,
      builder: (context) => const TimeoutDialog._(),
    );

    return switch (nav) {
      TimeoutDialogNav.retry => TimeoutDialogNav.retry,
      TimeoutDialogNav._scan when context.mounted =>
        switch (await Navigator.pushNamed(context, '/scanner')) {
          ScannerPageNav.ok => TimeoutDialogNav.retry,
          _ => null,
        },
      _ => null,
    };
  }

  @override
  Widget build(BuildContext context) {
    return AlertDialog(
      title: const Center(child: Text('請求狀態')),
      content: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          const Text('連線逾時', textAlign: TextAlign.center),
          const SizedBox(height: 20),
          DialogButtons.ternary(
            context,
            text1: '取消',
            onPressed1: () {
              Navigator.pop(context);
            },
            text2: '重試',
            onPressed2: () {
              Navigator.pop(context, TimeoutDialogNav.retry);
            },
            text3: '連接',
            onPressed3: () {
              Navigator.pop(context, TimeoutDialogNav._scan);
            },
          ),
        ],
      ),
    );
  }
}

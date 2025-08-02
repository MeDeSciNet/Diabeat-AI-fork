import 'package:diabeat/routes/connection/scanner.dart';
import 'package:diabeat/util.dart';
import 'package:flutter/material.dart';

enum DisconnectedDialogNav { ok }

class DisconnectedDialog extends StatelessWidget {
  const DisconnectedDialog._();

  static Future<dynamic> show(BuildContext context) async {
    final nav = await showDialog(
      context: context,
      builder: (context) => const DisconnectedDialog._(),
    );

    return switch (nav) {
      DisconnectedDialogNav.ok when context.mounted =>
        switch (await Navigator.pushNamed(context, '/scanner')) {
          ScannerPageNav.ok => DisconnectedDialogNav.ok,
          _ => null,
        },
      _ => null,
    };
  }

  @override
  Widget build(BuildContext context) {
    return AlertDialog(
      title: const Text('連線狀態', textAlign: TextAlign.center),
      content: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          const Text(
            '尚未連接到伺服器',
            textAlign: TextAlign.center,
            style: TextStyle(fontSize: 16),
          ),
          const SizedBox(height: 20),
          DialogButtons.binary(
            text1: '取消',
            onPressed1: () {
              Navigator.pop(context);
            },
            text2: '連接',
            onPressed2: () {
              Navigator.pop(context, DisconnectedDialogNav.ok);
            },
          ),
        ],
      ),
    );
  }
}

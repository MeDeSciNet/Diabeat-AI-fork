import 'package:diabeat/routes/network/scanner.dart';
import 'package:diabeat/util.dart' as util;
import 'package:flutter/material.dart';

class DisconnectedDialog extends StatelessWidget {
  const DisconnectedDialog._();

  /// connected    : true
  ///
  /// disconnected : null
  static Future<dynamic> show(BuildContext context) async {
    final nav = await showDialog(
      context: context,
      barrierDismissible: false,
      builder: (context) => const DisconnectedDialog._(),
    );
    if (!context.mounted) return;

    return switch (nav) {
      true => await ScannerPage.push(context),
      _ => null,
    };
  }

  @override
  Widget build(BuildContext context) {
    return AlertDialog(
      title: const Text('尚未連線到伺服器', textAlign: TextAlign.center),
      content: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          FilledButton.icon(
            onPressed: () {
              Navigator.pop(context, true);
            },
            style: util.filledPageButtonStyle(),
            icon: const Icon(Icons.qr_code_scanner_rounded),
            label: const Text('連線'),
          ),
          const SizedBox(height: 10),
          FilledButton.tonalIcon(
            onPressed: () {
              Navigator.pop(context);
            },
            style: util.tonalPageButtonStyle(context),
            icon: const Icon(Icons.close_rounded),
            label: const Text('取消'),
          ),
        ],
      ),
    );
  }
}

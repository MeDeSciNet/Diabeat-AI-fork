import 'package:diabeat/routes/network/scanner.dart';
import 'package:diabeat/util.dart' as util;
import 'package:flutter/material.dart';

enum _TimeoutDialogNav { scan, retry }

class TimeoutDialog extends StatelessWidget {
  const TimeoutDialog._();

  /// retry  : true
  ///
  /// cancel : null
  static Future<dynamic> show(BuildContext context) async {
    final nav = await showDialog(
      context: context,
      barrierDismissible: false,
      builder: (context) => const TimeoutDialog._(),
    );
    if (!context.mounted) return null;

    return switch (nav) {
      _TimeoutDialogNav.scan => await ScannerPage.push(context),
      _TimeoutDialogNav.retry => true,
      _ => null,
    };
  }

  @override
  Widget build(BuildContext context) {
    return AlertDialog(
      title: Text('連線逾時', textAlign: TextAlign.center),
      content: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          FilledButton.icon(
            onPressed: () {
              Navigator.pop(context, _TimeoutDialogNav.scan);
            },
            style: util.filledPageButtonStyle(),
            icon: const Icon(Icons.qr_code_scanner_rounded),
            label: const Text('連接'),
          ),
          const SizedBox(height: 10),
          FilledButton.tonalIcon(
            onPressed: () {
              Navigator.pop(context, _TimeoutDialogNav.retry);
            },
            style: util.tonalPageButtonStyle(context),
            icon: const Icon(Icons.replay_rounded),
            label: const Text('重試'),
          ),
          const SizedBox(height: 10),
          OutlinedButton.icon(
            onPressed: () {
              Navigator.pop(context);
            },
            style: util.outlinedPageButtonStyle(),
            icon: const Icon(Icons.close_rounded),
            label: const Text('取消'),
          ),
        ],
      ),
    );
  }
}

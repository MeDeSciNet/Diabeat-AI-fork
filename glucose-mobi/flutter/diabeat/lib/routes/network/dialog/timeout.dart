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
      builder: (context) => const TimeoutDialog._(),
    );

    return switch (nav) {
      _TimeoutDialogNav.scan when context.mounted => await Navigator.pushNamed(
        context,
        '/scanner',
      ),
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
            icon: const Icon(Icons.qr_code_scanner),
            label: const Text('連接'),
          ),
          const SizedBox(height: 10),
          FilledButton.tonalIcon(
            onPressed: () {
              Navigator.pop(context, _TimeoutDialogNav.retry);
            },
            style: util.tonalPageButtonStyle(context),
            icon: const Icon(Icons.replay),
            label: const Text('重試'),
          ),
          const SizedBox(height: 10),
          OutlinedButton.icon(
            onPressed: () {
              Navigator.pop(context);
            },
            style: util.outlinedPageButtonStyle(),
            icon: const Icon(Icons.close),
            label: const Text('取消'),
          ),
        ],
      ),
    );
  }
}

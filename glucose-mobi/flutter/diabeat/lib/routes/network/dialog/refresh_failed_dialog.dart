import 'package:diabeat/routes/network/session.dart' as session;
import 'package:diabeat/util.dart' as util;
import 'package:flutter/material.dart';

class RefreshFailedDialog extends StatelessWidget {
  const RefreshFailedDialog._();

  static Future<void> show(BuildContext context) async {
    await showDialog(
      context: context,
      barrierDismissible: false,
      builder: (context) => const RefreshFailedDialog._(),
    );
    if (!context.mounted) return;

    session.delete();
    Navigator.of(
      context,
      rootNavigator: true,
    ).pushNamedAndRemoveUntil('/guest', (route) => false);
  }

  @override
  Widget build(BuildContext context) {
    return AlertDialog(
      title: const Text('Token 刷新失敗', textAlign: TextAlign.center),
      content: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          FilledButton.icon(
            onPressed: () {
              Navigator.pop(context);
            },
            style: util.filledPageButtonStyle(),
            icon: const Icon(Icons.logout_rounded),
            label: const Text('登出'),
          ),
        ],
      ),
    );
  }
}

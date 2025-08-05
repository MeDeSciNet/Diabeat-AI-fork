import 'package:diabeat/routes/network/session.dart' as session;
import 'package:flutter/material.dart';

class RefreshFailedDialog extends StatelessWidget {
  const RefreshFailedDialog._();

  static void show(BuildContext context) {
    showDialog(
      context: context,
      barrierDismissible: false,
      builder: (context) => const RefreshFailedDialog._(),
    );
  }

  @override
  Widget build(BuildContext context) {
    return AlertDialog(
      title: const Center(child: Text('帳號異常')),
      content: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          const Text('Token 更新失敗', textAlign: TextAlign.center),
          const SizedBox(height: 20),
          FilledButton(
            onPressed: () {
              session.delete();
              Navigator.pushNamedAndRemoveUntil(
                context,
                '/guest',
                (route) => false,
              );
            },
            child: const Text('登出'),
          ),
        ],
      ),
    );
  }
}

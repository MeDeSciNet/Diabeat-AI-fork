import 'package:diabeat/util.dart' as util;
import 'package:flutter/material.dart';

enum ConfirmScanDialogNav { leave, ok }

class ConfirmScanDialog extends StatelessWidget {
  const ConfirmScanDialog._(this._addr);
  final String _addr;

  static Future show(BuildContext context, String addr) async {
    return await showDialog(
      context: context,
      barrierDismissible: false,
      builder: (context) => ConfirmScanDialog._(addr),
    );
  }

  @override
  Widget build(BuildContext context) {
    return AlertDialog(
      title: const Text('連線狀態', textAlign: TextAlign.center),
      content: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Text(
            '確定連接到 $_addr ?',
            textAlign: TextAlign.center,
            style: const TextStyle(fontSize: 16),
          ),
          const SizedBox(height: 20),
          util.ternaryDialogButtons(
            context,
            text1: '退出',
            onPressed1: () {
              Navigator.pop(context, ConfirmScanDialogNav.leave);
            },
            text2: '重試',
            onPressed2: () {
              Navigator.pop(context);
            },
            text3: '確定',
            onPressed3: () {
              Navigator.pop(context, ConfirmScanDialogNav.ok);
            },
          ),
        ],
      ),
    );
  }
}

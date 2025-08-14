import 'package:diabeat/util.dart' as util;
import 'package:flutter/material.dart';

class ConfirmScanDialog extends StatelessWidget {
  const ConfirmScanDialog._(this._addr);
  final String _addr;

  /// confirm scan : true
  ///
  /// re-scan      : null
  ///
  /// cancel scan  : false
  static Future<bool?> show(BuildContext context, String addr) {
    return showDialog(
      context: context,
      barrierDismissible: false,
      builder: (context) => ConfirmScanDialog._(addr),
    );
  }

  @override
  Widget build(BuildContext context) {
    return AlertDialog(
      title: const Text('連接到伺服器', textAlign: TextAlign.center),
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
          FilledButton.icon(
            onPressed: () {
              Navigator.pop(context, true);
            },
            style: util.filledPageButtonStyle(),
            icon: const Icon(Icons.check_rounded),
            label: const Text('確定'),
          ),
          const SizedBox(height: 10),
          FilledButton.tonalIcon(
            onPressed: () {
              Navigator.pop(context);
            },
            style: util.tonalPageButtonStyle(context),
            icon: const Icon(Icons.qr_code_scanner_rounded),
            label: const Text('重掃'),
          ),
          const SizedBox(height: 10),
          OutlinedButton.icon(
            onPressed: () {
              Navigator.pop(context, false);
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

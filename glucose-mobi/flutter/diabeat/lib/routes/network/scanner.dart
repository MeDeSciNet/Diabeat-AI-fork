import 'package:diabeat/routes/network/connection.dart' as connection;
import 'package:diabeat/routes/network/dialog/confirm_scan_dialog.dart';
import 'package:diabeat/util.dart' as util;
import 'package:flutter/material.dart';
import 'package:mobile_scanner/mobile_scanner.dart';

/// connected    : true
///
/// disconnected : null
class ScannerPage extends StatefulWidget {
  const ScannerPage({super.key});

  static Future<dynamic> push(BuildContext context) {
    return Navigator.of(context, rootNavigator: true).pushNamed('/scanner');
  }

  @override
  State<ScannerPage> createState() => _ScannerPageState();
}

class _ScannerPageState extends State<ScannerPage> {
  final _controller = MobileScannerController(
    formats: const [BarcodeFormat.qrCode],
  );
  final _scale = ValueNotifier<double>(0);

  void Function(BarcodeCapture) _detect(BuildContext context) {
    return (BarcodeCapture barcodes) async {
      final addrs = barcodes.barcodes.where(
        (element) => element.rawValue?.startsWith('Diabeat ') ?? false,
      );

      if (addrs.isEmpty) return;
      await _controller.stop(); // pause() has stupid bug

      if (!context.mounted) return;
      final addr = addrs.first.rawValue!.split(' ')[1];
      switch (await ConfirmScanDialog.show(context, addr)) {
        case true:
          connection.connectTo(addr);
          Navigator.pop(context, true);
          break;

        case false:
          Navigator.pop(context);
          break;

        default:
          _controller.start();
          break;
      }
    };
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: util.backAppBar(context, '連接到伺服器'),
      body: SafeArea(
        child: Column(
          children: [
            Expanded(
              child: MobileScanner(
                controller: _controller,
                onDetect: _detect(context),
              ),
            ),
            Padding(
              padding: const EdgeInsets.symmetric(vertical: 20, horizontal: 40),
              child: ValueListenableBuilder(
                valueListenable: _scale,
                builder: (context, value, child) => Slider(
                  value: _scale.value,
                  onChanged: (value) {
                    setState(() => _scale.value = value);
                    _controller.setZoomScale(_scale.value);
                  },
                  year2023: false,
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

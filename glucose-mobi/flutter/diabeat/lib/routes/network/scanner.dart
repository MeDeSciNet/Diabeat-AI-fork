import 'package:diabeat/routes/network/connection.dart' as connection;
import 'package:diabeat/routes/network/dialog/confirm_scan_dialog.dart';
import 'package:flutter/material.dart';
import 'package:mobile_scanner/mobile_scanner.dart';

/// connected    : true
///
/// disconnected : null
class ScannerPage extends StatelessWidget {
  ScannerPage({super.key});
  final _controller = MobileScannerController(
    formats: const [BarcodeFormat.qrCode],
  );

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
      appBar: AppBar(
        leading: IconButton(
          onPressed: () {
            Navigator.pop(context);
          },
          icon: const Icon(Icons.arrow_back_ios_new),
        ),
        title: const Text('連接到伺服器'),
        centerTitle: true,
      ),
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
              child: _SliderWidget(_controller),
            ),
          ],
        ),
      ),
    );
  }
}

class _SliderWidget extends StatefulWidget {
  const _SliderWidget(this.controller);
  final MobileScannerController controller;

  @override
  State<_SliderWidget> createState() => _SliderWidgetState();
}

class _SliderWidgetState extends State<_SliderWidget> {
  double _scale = 0;

  @override
  Widget build(BuildContext context) {
    return Slider(
      value: _scale,
      onChanged: (value) {
        setState(() => _scale = value);
        widget.controller.setZoomScale(_scale);
      },
      year2023: false,
    );
  }
}

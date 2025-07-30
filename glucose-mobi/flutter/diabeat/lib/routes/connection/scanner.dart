import 'package:diabeat/routes/connection/request.dart';
import 'package:diabeat/util.dart';
import 'package:flutter/material.dart';
import 'package:mobile_scanner/mobile_scanner.dart';

enum ScannerPageNav { ok }

class ScannerPage extends StatelessWidget {
  ScannerPage({super.key});
  final _controller = MobileScannerController(formats: [BarcodeFormat.qrCode]);

  void Function(BarcodeCapture) _detect(BuildContext context) {
    return (BarcodeCapture barcodes) async {
      final addrs = barcodes.barcodes.where(
        (element) => element.rawValue?.startsWith('Diabeat ') ?? false,
      );

      if (addrs.isEmpty) return;
      await _controller.stop(); // pause() has stupid bug

      if (!context.mounted) return;
      final addr = addrs.first.rawValue!.split(' ')[1];
      switch (await _ConfirmScanDialog.show(context, addr)) {
        case _ConfirmScanDialogNav.leave:
          Navigator.pop(context);
          break;

        case _ConfirmScanDialogNav.ok:
          Request.setAddr(addr);
          Navigator.pop(context, ScannerPageNav.ok);
          break;

        default:
          _controller.start();
          break;
      }
    };
  }

  @override
  Widget build(BuildContext context) {
    return Material(
      child: SafeArea(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.spaceEvenly,
          children: [
            Stack(
              children: [
                AspectRatio(
                  aspectRatio: 9 / 16,
                  child: MobileScanner(
                    controller: _controller,
                    onDetect: _detect(context),
                  ),
                ),
                IconButton(
                  onPressed: () {
                    Navigator.pop(context);
                  },
                  icon: const Icon(Icons.arrow_back_ios_new),
                ),
              ],
            ),
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 20),
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
      year2023: false, // deprecated
    );
  }
}

enum _ConfirmScanDialogNav { leave, ok }

class _ConfirmScanDialog extends StatelessWidget {
  const _ConfirmScanDialog._(this._addr);
  final String _addr;

  static Future show(BuildContext context, String addr) async {
    return await showDialog(
      context: context,
      barrierDismissible: false,
      builder: (context) => _ConfirmScanDialog._(addr),
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
          DialogButtons.ternary(
            context,
            text1: '退出',
            onPressed1: () {
              Navigator.pop(context, _ConfirmScanDialogNav.leave);
            },
            text2: '重試',
            onPressed2: () {
              Navigator.pop(context);
            },
            text3: '確定',
            onPressed3: () {
              Navigator.pop(context, _ConfirmScanDialogNav.ok);
            },
          ),
        ],
      ),
    );
  }
}

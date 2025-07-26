import 'dart:developer';
import 'package:diabeat/routes/connection/request.dart';
import 'package:diabeat/util.dart';
import 'package:flutter/material.dart';
import 'package:mobile_scanner/mobile_scanner.dart';

class ScannerPage extends StatelessWidget {
  ScannerPage({super.key});

  final _controller = MobileScannerController(formats: [BarcodeFormat.qrCode]);

  Future<void> _detect(BuildContext context, BarcodeCapture barcodes) async {
    final addrs = barcodes.barcodes.where(
      (element) => element.rawValue?.startsWith('Diabeat ') ?? false,
    );

    if (addrs.isEmpty) return;
    await _controller.stop(); // pause() has stupid bug

    if (!context.mounted) return;
    final addr = addrs.first.rawValue!.split(' ')[1];
    final res = await _ConfirmScanDialog.show(context, addr);

    if (res == null) {
      await _controller.start();
      return;
    }

    if (res == '!exit') {
      if (context.mounted) {
        Navigator.pop(context, null);
      }
      return;
    }

    // res == '!ok'
    await Request.setAddr(addr);
    if (context.mounted) {
      Navigator.pop(context, '!ok');
      log('okokok');
    }
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
                    onDetect: (barcodes) async {
                      await _detect(context, barcodes);
                    },
                  ),
                ),
                IconButton(
                  onPressed: () {
                    Navigator.pop(context);
                  },
                  icon: const Icon(Icons.arrow_back_ios_new_rounded),
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
      onChanged: (value) async {
        setState(() => _scale = value);

        await widget.controller.setZoomScale(_scale);
      },
      year2023: false, // deprecated
    );
  }
}

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
          Row(
            children: [
              Expanded(
                child: OutlinedButton(
                  onPressed: () {
                    Navigator.pop(context, '!exit');
                  },
                  style: BtnStyleExt.dialogNeg,
                  child: const Text('返回'),
                ),
              ),
              const SizedBox(width: 10),
              Expanded(
                child: FilledButton.tonal(
                  onPressed: () {
                    Navigator.pop(context, null);
                  },
                  style: BtnStyleExt.dialogNeu(context),
                  child: const Text('重試'),
                ),
              ),
              const SizedBox(width: 10),
              Expanded(
                child: FilledButton(
                  onPressed: () {
                    Navigator.pop(context, '!ok');
                  },
                  style: BtnStyleExt.dialogPos,
                  child: const Text('確定'),
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }
}

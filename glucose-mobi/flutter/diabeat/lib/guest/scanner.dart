import 'package:flutter/material.dart';
import 'package:mobile_scanner/mobile_scanner.dart';
import 'package:path_provider/path_provider.dart';
import 'dart:io';
import '../util.dart';

/* */
/* */
/* ===== Scanner ===== */

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
    await _ConfirmScanDialog.show(context, addr, _controller);
  }

  @override
  Widget build(context) => Material(
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
                  onDetect: (barcodes) async =>
                      await _detect(context, barcodes),
                ),
              ),
              IconButton(
                onPressed: () => Navigator.pop(context),
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

class _SliderWidget extends StatefulWidget {
  const _SliderWidget(this.controller);

  final MobileScannerController controller;

  @override
  State<_SliderWidget> createState() => _SliderWidgetState();
}

class _SliderWidgetState extends State<_SliderWidget> {
  double _scale = 0;

  @override
  Widget build(context) => Slider(
    value: _scale,
    onChanged: (value) async {
      setState(() => _scale = value);
      await widget.controller.setZoomScale(_scale);
    },
    year2023: false, // deprecated
  );
}

class _ConfirmScanDialog extends StatelessWidget {
  const _ConfirmScanDialog._(this._addr, this._controller);

  final String _addr;
  final MobileScannerController _controller;

  static Future<void> show(
    BuildContext context,
    String addr,
    MobileScannerController controller,
  ) async => await showDialog(
    context: context,
    builder: (context) => _ConfirmScanDialog._(addr, controller),
  );

  Future<void> _save(BuildContext context) async {
    final cacheDir = await getTemporaryDirectory();
    final file = File('${cacheDir.path}/addr.txt');
    await file.writeAsString('$_addr\n');
  }

  @override
  Widget build(context) => AlertDialog(
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
                onPressed: () async {
                  await _controller.start();

                  if (!context.mounted) return;
                  Navigator.pop(context);
                },
                style: BtnStyleExt.dialogNeg,
                child: const Text('取消'),
              ),
            ),
            const SizedBox(width: 10),
            Expanded(
              child: FilledButton(
                onPressed: () async {
                  await _save(context);

                  if (!context.mounted) return;
                  Navigator.pop(context);
                  Navigator.pop(context);
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

/* */
/* */
/* ===== Dialogs ===== */

class DisconnectedDialog extends StatelessWidget {
  const DisconnectedDialog._();

  static Future<void> show(BuildContext context) async => await showDialog(
    context: context,
    builder: (context) => const DisconnectedDialog._(),
  );

  @override
  Widget build(context) => AlertDialog(
    title: const Text('連線狀態', textAlign: TextAlign.center),
    content: Column(
      mainAxisSize: MainAxisSize.min,
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        const Text(
          '尚未連接到伺服器',
          textAlign: TextAlign.center,
          style: TextStyle(fontSize: 16),
        ),
        const SizedBox(height: 20),
        Row(
          children: [
            Expanded(
              child: OutlinedButton(
                onPressed: () => Navigator.pop(context),
                style: BtnStyleExt.dialogNeg,
                child: const Text('取消'),
              ),
            ),
            const SizedBox(width: 10),
            Expanded(
              child: FilledButton(
                onPressed: () {
                  Navigator.pop(context);
                  navigate(context, (_) => ScannerPage());
                },
                style: BtnStyleExt.dialogPos,
                child: const Text('掃描'),
              ),
            ),
          ],
        ),
      ],
    ),
  );
}

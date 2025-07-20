import 'dart:io';
import 'package:flutter/material.dart';
import 'package:mobile_scanner/mobile_scanner.dart';
import 'package:path_provider/path_provider.dart';

class ScannerPage extends StatelessWidget {
  const ScannerPage({super.key});

  @override
  Widget build(context) {
    final controller = MobileScannerController(formats: [BarcodeFormat.qrCode]);

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
                    controller: controller,
                    onDetect: (barcodes) async {
                      final addrs = barcodes.barcodes.where(
                        (element) =>
                            element.rawValue?.startsWith('Diabeat ') ?? false,
                      );

                      if (addrs.isNotEmpty) {
                        await controller.pause();

                        final addr = addrs.first.rawValue!.split(' ')[1];

                        final cacheDir = await getTemporaryDirectory();
                        final file = File('${cacheDir.path}/addr.txt');
                        await file.writeAsString('$addr\n');

                        // idk
                        if (context.mounted) {
                          Navigator.pop(context);
                        }
                      }
                    },
                  ),
                ),
                IconButton(
                  onPressed: () {
                    Navigator.pop(context);
                  },
                  iconSize: 50,
                  icon: Icon(Icons.keyboard_arrow_left_rounded),
                ),
              ],
            ),
            Padding(
              padding: EdgeInsets.symmetric(horizontal: 20),
              child: SliderWidget(controller),
            ),
          ],
        ),
      ),
    );
  }
}

class SliderWidget extends StatefulWidget {
  const SliderWidget(this.controller, {super.key});

  final MobileScannerController controller;

  @override
  State<SliderWidget> createState() => _SliderWidgetState();
}

class _SliderWidgetState extends State<SliderWidget> {
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

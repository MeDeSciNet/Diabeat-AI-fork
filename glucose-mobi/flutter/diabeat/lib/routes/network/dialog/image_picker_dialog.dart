import 'package:diabeat/util.dart' as util;
import 'package:flutter/material.dart';

enum ImagePickerDialogNav { camera, gallery }

class ImagePickerDialog extends StatelessWidget {
  const ImagePickerDialog._();

  static Future<ImagePickerDialogNav?> show(BuildContext context) {
    return showDialog(
      context: context,
      builder: (context) => const ImagePickerDialog._(),
    );
  }

  @override
  Widget build(BuildContext context) => AlertDialog(
    title: Text('選擇來源', textAlign: TextAlign.center),
    content: Column(
      mainAxisSize: MainAxisSize.min,
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        FilledButton.icon(
          onPressed: () {
            Navigator.pop(context, ImagePickerDialogNav.camera);
          },
          style: util.filledPageButtonStyle(),
          label: const Text('拍照'),
          icon: const Icon(Icons.camera_alt),
        ),
        const SizedBox(height: 10),
        OutlinedButton.icon(
          onPressed: () {
            Navigator.pop(context, ImagePickerDialogNav.gallery);
          },
          style: util.outlinedPageButtonStyle(),
          icon: const Icon(Icons.photo),
          label: const Text('圖庫'),
        ),
      ],
    ),
  );
}

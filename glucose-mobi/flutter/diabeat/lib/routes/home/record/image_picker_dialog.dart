import 'package:diabeat/util.dart' as util;
import 'package:flutter/material.dart';
import 'package:image_picker/image_picker.dart';

class ImagePickerDialog extends StatelessWidget {
  const ImagePickerDialog._();

  static Future<ImageSource?> show(BuildContext context) {
    return showDialog(
      context: context,
      builder: (context) => const ImagePickerDialog._(),
    );
  }

  @override
  Widget build(BuildContext context) => AlertDialog(
    title: const Text('選擇來源', textAlign: TextAlign.center),
    content: Column(
      mainAxisSize: MainAxisSize.min,
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        FilledButton.icon(
          onPressed: () {
            Navigator.pop(context, ImageSource.camera);
          },
          style: util.filledPageButtonStyle(),
          label: const Text('拍照'),
          icon: const Icon(Icons.camera_alt_rounded),
        ),
        const SizedBox(height: 10),
        OutlinedButton.icon(
          onPressed: () {
            Navigator.pop(context, ImageSource.gallery);
          },
          style: util.outlinedPageButtonStyle(),
          icon: const Icon(Icons.photo_rounded),
          label: const Text('圖庫'),
        ),
      ],
    ),
  );
}

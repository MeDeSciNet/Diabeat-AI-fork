import 'package:diabeat/util.dart' as util;
import 'package:flutter/material.dart';

enum PdfCsvEnum { pdf, csv }

class PdfCsvDialog extends StatelessWidget {
  const PdfCsvDialog._();

  static Future<PdfCsvEnum?> show(BuildContext context) {
    return showDialog(
      context: context,
      builder: (context) => const PdfCsvDialog._(),
    );
  }

  @override
  Widget build(BuildContext context) {
    return AlertDialog(
      title: const Text('分享為', textAlign: TextAlign.center),
      content: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          FilledButton(
            onPressed: () {
              Navigator.pop(context, PdfCsvEnum.pdf);
            },
            style: util.filledPageButtonStyle(),
            child: const Text('PDF'),
          ),
          const SizedBox(height: 10),
          FilledButton.tonal(
            onPressed: () {
              Navigator.pop(context, PdfCsvEnum.csv);
            },
            style: util.tonalPageButtonStyle(context),
            child: const Text('CSV'),
          ),
        ],
      ),
    );
  }
}

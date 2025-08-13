import 'package:diabeat/routes/network/scanner.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

ButtonStyle filledPageButtonStyle() {
  return FilledButton.styleFrom(
    fixedSize: const Size.fromHeight(50),
    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(5)),
  );
}

ButtonStyle tonalPageButtonStyle(BuildContext context) {
  return FilledButton.styleFrom(
    backgroundColor: ColorScheme.of(context).secondaryContainer,
    foregroundColor: ColorScheme.of(context).onSecondaryContainer,
    fixedSize: const Size.fromHeight(50),
    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(5)),
  );
}

ButtonStyle outlinedPageButtonStyle() {
  return OutlinedButton.styleFrom(
    fixedSize: const Size.fromHeight(50),
    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(5)),
  );
}

Widget backButton(BuildContext context) {
  return IconButton(
    onPressed: () {
      Navigator.pop(context);
    },
    icon: const Icon(Icons.arrow_back_ios_new_rounded),
  );
}

Widget scanButton(BuildContext context) {
  return IconButton(
    onPressed: () {
      ScannerPage.push(context);
    },
    icon: const Icon(Icons.qr_code_scanner_rounded),
  );
}

InputDecoration inputBorder(String label) {
  return InputDecoration(labelText: label, border: const OutlineInputBorder());
}

String? nonEmptyValidator(String? value) {
  return value == null || value.isEmpty ? '必填' : null;
}

class UdoubleFormatter extends TextInputFormatter {
  const UdoubleFormatter();

  @override
  TextEditingValue formatEditUpdate(
    TextEditingValue oldValue,
    TextEditingValue newValue,
  ) {
    final newText = newValue.text;
    if (newText.isEmpty) {
      return newValue;
    }

    final value = double.tryParse(newText);
    return value == null || value < 0 ? oldValue : newValue;
  }
}

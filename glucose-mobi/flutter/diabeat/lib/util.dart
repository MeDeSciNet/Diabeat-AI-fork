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

class UDoubleFieldManager {
  final ctrl = TextEditingController();
  final focusNode = FocusNode();

  double? get value => double.tryParse(ctrl.text);
  set text(String value) {
    ctrl.text = value;
  }

  void dispose() {
    ctrl.dispose();
    focusNode.dispose();
  }

  void Function(String) focus() {
    return (value) {
      focusNode.requestFocus();
    };
  }

  void clear() {
    ctrl.clear();
  }
}

class UdoubleFormatter extends TextInputFormatter {
  const UdoubleFormatter();

  @override
  TextEditingValue formatEditUpdate(
    TextEditingValue oldValue,
    TextEditingValue newValue,
  ) {
    if (newValue.text.isEmpty) return newValue;

    final value = double.tryParse(newValue.text);
    if (value == null || value < 0) {
      return oldValue;
    }

    return newValue;
  }
}

List<TextInputFormatter> makeUdoubleFormatter() {
  return const [UdoubleFormatter()];
}

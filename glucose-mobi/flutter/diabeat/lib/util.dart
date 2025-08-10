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

Widget prevPageButton(void Function() onPressed) {
  return Expanded(
    child: OutlinedButton.icon(
      onPressed: onPressed,
      style: outlinedPageButtonStyle(),
      icon: const Icon(Icons.arrow_back_ios_new),
      label: const Text('上一頁'),
    ),
  );
}

Widget nextPageButton(void Function() onPressed) {
  return Expanded(
    child: FilledButton.icon(
      onPressed: onPressed,
      style: filledPageButtonStyle(),
      icon: const Icon(Icons.arrow_forward_ios),
      iconAlignment: IconAlignment.end,
      label: const Text('下一頁'),
    ),
  );
}

String? stringValidator(String? value) {
  return value == null || value.isEmpty ? '必填' : null;
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
    final newText = newValue.text;
    if (newText.isEmpty) {
      return newValue;
    }

    final value = double.tryParse(newText);
    return value == null || value < 0 ? oldValue : newValue;
  }
}

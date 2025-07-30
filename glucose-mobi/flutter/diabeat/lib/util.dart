import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

class PageButtons {
  PageButtons._();

  static ButtonStyle get filled => FilledButton.styleFrom(
    fixedSize: const Size.fromHeight(50),
    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(5)),
  );

  static ButtonStyle get outlined => OutlinedButton.styleFrom(
    fixedSize: const Size.fromHeight(50),
    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(5)),
  );
}

class DialogButtons {
  DialogButtons._();

  static ButtonStyle _leftButtonStyle() {
    return OutlinedButton.styleFrom(
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.horizontal(left: Radius.circular(10000)),
      ),
    );
  }

  static ButtonStyle _middleButtonStyle(BuildContext context) {
    return FilledButton.styleFrom(
      backgroundColor: ColorScheme.of(context).secondaryContainer,
      foregroundColor: ColorScheme.of(context).onSecondaryContainer,
      shape: const RoundedRectangleBorder(),
    );
  }

  static ButtonStyle _rightButtonStyle() {
    return FilledButton.styleFrom(
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.horizontal(right: Radius.circular(10000)),
      ),
    );
  }

  static Row binary({
    required String text1,
    required void Function() onPressed1,
    required String text2,
    required void Function() onPressed2,
  }) {
    return Row(
      children: [
        Expanded(
          child: OutlinedButton(
            onPressed: onPressed1,
            style: _leftButtonStyle(),
            child: Text(text1),
          ),
        ),
        const SizedBox(width: 10),
        Expanded(
          child: FilledButton(
            onPressed: onPressed2,
            style: _rightButtonStyle(),
            child: Text(text2),
          ),
        ),
      ],
    );
  }

  static Row ternary(
    BuildContext context, {
    required String text1,
    required void Function() onPressed1,
    required String text2,
    required void Function() onPressed2,
    required String text3,
    required void Function() onPressed3,
  }) {
    return Row(
      children: [
        Expanded(
          child: OutlinedButton(
            onPressed: onPressed1,
            style: _leftButtonStyle(),
            child: Text(text1),
          ),
        ),
        const SizedBox(width: 10),
        Expanded(
          child: FilledButton.tonal(
            onPressed: onPressed2,
            style: _middleButtonStyle(context),
            child: Text(text2),
          ),
        ),
        const SizedBox(width: 10),
        Expanded(
          child: FilledButton(
            onPressed: onPressed3,
            style: _rightButtonStyle(),
            child: Text(text3),
          ),
        ),
      ],
    );
  }
}

class NonNegativeNumberFormatter extends TextInputFormatter {
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

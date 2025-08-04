import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

ButtonStyle filledPageButtonStyle() {
  return FilledButton.styleFrom(
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

/* */
/* */
/* */

ButtonStyle _leftButtonStyle() {
  return OutlinedButton.styleFrom(
    shape: const RoundedRectangleBorder(
      borderRadius: BorderRadius.horizontal(left: Radius.circular(10000)),
    ),
  );
}

ButtonStyle _middleButtonStyle(BuildContext context) {
  return FilledButton.styleFrom(
    backgroundColor: ColorScheme.of(context).secondaryContainer,
    foregroundColor: ColorScheme.of(context).onSecondaryContainer,
    shape: const RoundedRectangleBorder(),
  );
}

ButtonStyle _rightButtonStyle() {
  return FilledButton.styleFrom(
    shape: const RoundedRectangleBorder(
      borderRadius: BorderRadius.horizontal(right: Radius.circular(10000)),
    ),
  );
}

Row binaryDialogButtons({
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

Row ternaryDialogButtons(
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

/* */
/* */
/* */

class _NonNegativeNumberFormatter extends TextInputFormatter {
  const _NonNegativeNumberFormatter();

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

List<TextInputFormatter> nonNegativeNumberFormatters() {
  return const [_NonNegativeNumberFormatter()];
}

import 'package:flutter/material.dart';

class BtnStyleExt {
  BtnStyleExt._();

  static ButtonStyle get mainFilled => FilledButton.styleFrom(
    fixedSize: const Size.fromHeight(50),
    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(5)),
  );

  static ButtonStyle get mainOutlined => OutlinedButton.styleFrom(
    fixedSize: const Size.fromHeight(50),
    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(5)),
  );

  static ButtonStyle get dialogPos => FilledButton.styleFrom(
    shape: const RoundedRectangleBorder(
      borderRadius: BorderRadius.horizontal(
        right: Radius.circular(10000), // casual big number,
      ),
    ),
  );

  static ButtonStyle dialogNeu(BuildContext context) => FilledButton.styleFrom(
    backgroundColor: ColorScheme.of(context).secondaryContainer,
    foregroundColor: ColorScheme.of(context).onSecondaryContainer,
    shape: const RoundedRectangleBorder(),
  );

  static ButtonStyle get dialogNeg => OutlinedButton.styleFrom(
    shape: const RoundedRectangleBorder(
      borderRadius: BorderRadius.horizontal(
        left: Radius.circular(10000), // casual big number,
      ),
    ),
  );
}

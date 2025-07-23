import 'package:flutter/material.dart';

MaterialPageRoute _route(Widget Function(BuildContext) builder) =>
    MaterialPageRoute(builder: builder);

Navigator navigator(Widget Function(BuildContext) builder) =>
    Navigator(onGenerateRoute: (_) => _route(builder));

Future<void> navigate(
  BuildContext context,
  Widget Function(BuildContext) builder,
) async {
  await Navigator.push(context, _route(builder));
}

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
      borderRadius: BorderRadius.horizontal(right: Radius.circular(10)),
    ),
  );

  static ButtonStyle get dialogNeg => OutlinedButton.styleFrom(
    shape: const RoundedRectangleBorder(
      borderRadius: BorderRadius.horizontal(left: Radius.circular(10)),
    ),
  );
}

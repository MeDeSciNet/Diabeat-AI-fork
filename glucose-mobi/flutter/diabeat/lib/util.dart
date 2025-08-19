import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

/* */
/* */
/* ===== UI ===== */

ButtonStyle filledPageButtonStyle() {
  return FilledButton.styleFrom(
    fixedSize: const Size.fromHeight(56),
    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
  );
}

ButtonStyle tonalPageButtonStyle(BuildContext context) {
  return FilledButton.styleFrom(
    backgroundColor: ColorScheme.of(context).secondaryContainer,
    foregroundColor: ColorScheme.of(context).onSecondaryContainer,
    fixedSize: const Size.fromHeight(56),
    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
  );
}

ButtonStyle outlinedPageButtonStyle() {
  return OutlinedButton.styleFrom(
    fixedSize: const Size.fromHeight(56),
    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
  );
}

Widget backIconButton(BuildContext context) {
  return IconButton(
    onPressed: () {
      Navigator.pop(context);
    },
    icon: const Icon(Icons.arrow_back_ios_new_rounded),
  );
}

Widget scanIconButton(BuildContext context, {required bool waiting}) {
  return IconButton(
    onPressed: waiting
        ? null
        : () {
            Navigator.of(context, rootNavigator: true).pushNamed('/scanner');
          },
    icon: const Icon(Icons.qr_code_scanner_rounded),
  );
}

Widget smallCircularProgressIndicator() {
  return Transform.scale(
    scale: 0.5,
    child: const CircularProgressIndicator(year2023: false),
  );
}

InputDecoration inputBorder(String label) {
  return InputDecoration(labelText: label, border: const OutlineInputBorder());
}

void formUnfocus(GlobalKey<FormState> formKey) {
  FocusScope.of(formKey.currentContext!).unfocus();
}

/* */
/* */
/* ===== Card X ListTile X Table ===== */

Widget figureCard(String title, List<(String, dynamic, String?)> rows) {
  return Card.outlined(
    child: ListTile(
      title: Text(title),
      subtitle: Table(
        columnWidths: const {
          0: IntrinsicColumnWidth(),
          1: IntrinsicColumnWidth(),
          2: IntrinsicColumnWidth(),
          3: IntrinsicColumnWidth(),
          4: FlexColumnWidth(),
        },
        children: rows.map((e) {
          final (col1, col2, col3) = e;
          final haveCol2 = col2 != null;
          final haveCol3 = col3 != null;

          return TableRow(
            children: [
              Text(col1),
              const SizedBox(width: 20),
              haveCol2 ? Text(col2.toString()) : const SizedBox(),
              const SizedBox(width: 20),
              haveCol3
                  ? (haveCol2 ? Text(col3) : const SizedBox())
                  : const SizedBox(),
            ],
          );
        }).toList(),
      ),
    ),
  );
}

/* */
/* */
/* ===== Misc ===== */

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

String? nonEmptyValidator(String? value) {
  return value == null || value.isEmpty ? '必填' : null;
}

String pad2Zero(dynamic obj) {
  return obj.toString().padLeft(2, '0');
}

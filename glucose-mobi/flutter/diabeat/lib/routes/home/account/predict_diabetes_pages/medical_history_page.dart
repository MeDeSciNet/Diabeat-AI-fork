import 'package:diabeat/util.dart' as util;
import 'package:flutter/material.dart';

class MedicalHistoryPage extends StatefulWidget {
  const MedicalHistoryPage({
    super.key,
    required this.goPrevPage,
    required this.goNextPage,
  });
  final void Function() goPrevPage;
  final void Function() goNextPage;

  @override
  State<MedicalHistoryPage> createState() => MedicalHistoryPageState();
}

class MedicalHistoryPageState extends State<MedicalHistoryPage> {
  final _formKey = GlobalKey<FormState>();
  bool hypertension = false;
  bool heartDisease = false;
  String? smokingHistory;

  @override
  Widget build(BuildContext context) {
    return Form(
      key: _formKey,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          const Text('疾病史'),
          CheckboxListTile(
            title: const Text('高血壓'),
            value: hypertension,
            onChanged: (value) {
              setState(() => hypertension = value!);
            },
            controlAffinity: ListTileControlAffinity.leading,
          ),
          CheckboxListTile(
            title: const Text('心臟病'),
            value: heartDisease,
            onChanged: (value) {
              setState(() => heartDisease = value!);
            },
            controlAffinity: ListTileControlAffinity.leading,
          ),
          const SizedBox(height: 20),
          FormField<String>(
            validator: util.stringValidator,
            autovalidateMode: AutovalidateMode.onUserInteraction,
            onSaved: (newValue) => smokingHistory = newValue,
            builder: (field) => Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                Text.rich(
                  TextSpan(
                    text: '吸菸史 ',
                    children: [
                      if (field.hasError)
                        TextSpan(
                          text: '(必填)',
                          style: const TextStyle(color: Colors.red),
                        ),
                    ],
                  ),
                ),
                ...[
                  ('從不吸菸', 'never'),
                  ('曾經吸菸', 'former'),
                  ('目前沒有吸菸', 'not current'),
                  ('目前有吸菸', 'current'),
                ].map(
                  (e) => RadioListTile(
                    title: Text(e.$1),
                    value: e.$2,
                    groupValue: field.value,
                    onChanged: field.didChange,
                  ),
                ),
              ],
            ),
          ),
          const Spacer(),
          Row(
            children: [
              util.prevPageButton(widget.goPrevPage),
              const SizedBox(width: 20),
              util.nextPageButton(_tryGoNextPage),
            ],
          ),
        ],
      ),
    );
  }

  void _tryGoNextPage() {
    final formState = _formKey.currentState!;
    if (formState.validate()) {
      formState.save();
      widget.goNextPage();
    }
  }
}

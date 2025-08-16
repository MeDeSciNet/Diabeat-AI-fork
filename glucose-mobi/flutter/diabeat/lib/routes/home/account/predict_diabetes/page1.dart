import 'package:diabeat/routes/home/account/predict_diabetes/fields.dart';
import 'package:diabeat/util.dart' as util;
import 'package:flutter/material.dart';

class Page1 extends StatefulWidget {
  const Page1({super.key});

  @override
  State<Page1> createState() => _Page1State();
}

class _Page1State extends State<Page1> {
  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        const Text('疾病史'),
        CheckboxListTile(
          title: const Text('高血壓'),
          value: PredictDiabetesField().hypertension,
          onChanged: (value) {
            setState(() => PredictDiabetesField().hypertension = value!);
          },
          controlAffinity: ListTileControlAffinity.leading,
        ),
        CheckboxListTile(
          title: const Text('心臟病'),
          value: PredictDiabetesField().heartDisease,
          onChanged: (value) {
            setState(() => PredictDiabetesField().heartDisease = value!);
          },
          controlAffinity: ListTileControlAffinity.leading,
        ),
        const SizedBox(height: 20),
        FormField<String>(
          validator: util.nonEmptyValidator,
          onSaved: (newValue) {
            PredictDiabetesField().smokingHistory = newValue;
          },
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
      ],
    );
  }
}

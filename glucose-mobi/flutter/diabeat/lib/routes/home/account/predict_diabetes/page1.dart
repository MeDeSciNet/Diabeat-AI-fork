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
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text('疾病史', style: TextStyle(fontSize: 16)),
        CheckboxListTile(
          title: const Text('高血壓'),
          value: PredictDiabetesFields.hypertension,
          onChanged: (value) {
            setState(() => PredictDiabetesFields.hypertension = value!);
          },
          controlAffinity: ListTileControlAffinity.leading,
        ),
        CheckboxListTile(
          title: const Text('心臟病', style: TextStyle(fontSize: 16)),
          value: PredictDiabetesFields.heartDisease,
          onChanged: (value) {
            setState(() => PredictDiabetesFields.heartDisease = value!);
          },
          controlAffinity: ListTileControlAffinity.leading,
        ),
        const SizedBox(height: 20),
        FormField<String>(
          validator: util.nonEmptyValidator,
          onSaved: (newValue) {
            PredictDiabetesFields.smokingHistory = newValue;
          },
          builder: (field) => Column(
            crossAxisAlignment: CrossAxisAlignment.start,
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
                style: TextStyle(fontSize: 16),
              ),
              ...PredictDiabetesFields.smokingHistoryMap.entries.map(
                (e) => RadioListTile(
                  title: Text(e.value),
                  value: e.key,
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

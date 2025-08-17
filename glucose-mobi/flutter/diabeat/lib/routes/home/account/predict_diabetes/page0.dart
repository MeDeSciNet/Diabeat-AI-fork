import 'package:diabeat/routes/home/account/predict_diabetes/fields.dart';
import 'package:diabeat/util.dart' as util;
import 'package:flutter/material.dart';

class Page0 extends StatelessWidget {
  Page0({super.key});
  final _heightFocus = FocusNode();
  final _weightFocus = FocusNode();

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        FormField<String>(
          validator: util.nonEmptyValidator,
          onSaved: (newValue) {
            PredictDiabetesFields.gender = newValue;
          },
          builder: (field) => Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text.rich(
                TextSpan(
                  text: '性別 ',
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
              RadioListTile(
                title: const Text('男'),
                value: 'male',
                groupValue: field.value,
                onChanged: field.didChange,
              ),
              RadioListTile(
                title: const Text('女'),
                value: 'female',
                groupValue: field.value,
                onChanged: field.didChange,
              ),
            ],
          ),
        ),
        const SizedBox(height: 10),
        TextFormField(
          keyboardType: TextInputType.number,
          textInputAction: TextInputAction.next,
          onFieldSubmitted: (value) {
            _heightFocus.requestFocus();
          },
          decoration: util.inputBorder('年齡'),
          validator: util.nonEmptyValidator,
          onSaved: (newValue) {
            PredictDiabetesFields.age = int.parse(newValue!);
          },
        ),
        const SizedBox(height: 20),
        TextFormField(
          focusNode: _heightFocus,
          keyboardType: TextInputType.numberWithOptions(decimal: true),
          inputFormatters: const [util.UdoubleFormatter()],
          textInputAction: TextInputAction.next,
          onFieldSubmitted: (value) {
            _weightFocus.requestFocus();
          },
          decoration: util.inputBorder('身高 (cm)'),
          validator: util.nonEmptyValidator,
          onSaved: (newValue) {
            PredictDiabetesFields.height = double.parse(newValue!);
          },
        ),
        const SizedBox(height: 20),
        TextFormField(
          focusNode: _weightFocus,
          keyboardType: TextInputType.numberWithOptions(decimal: true),
          inputFormatters: const [util.UdoubleFormatter()],
          textInputAction: TextInputAction.done,
          decoration: util.inputBorder('體重 (kg)'),
          validator: util.nonEmptyValidator,
          onSaved: (newValue) {
            PredictDiabetesFields.weight = double.parse(newValue!);
          },
        ),
      ],
    );
  }
}

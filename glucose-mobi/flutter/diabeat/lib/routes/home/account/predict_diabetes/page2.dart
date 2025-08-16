import 'package:diabeat/routes/home/account/predict_diabetes/fields.dart';
import 'package:diabeat/util.dart' as util;
import 'package:flutter/material.dart';

class Page2 extends StatelessWidget {
  Page2({super.key});
  final _hba1cFocus = FocusNode();

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        TextFormField(
          validator: util.nonEmptyValidator,
          onSaved: (newValue) {
            PredictDiabetesField().glucose = double.parse(newValue!);
          },
          keyboardType: TextInputType.numberWithOptions(decimal: true),
          inputFormatters: const [util.UdoubleFormatter()],
          textInputAction: TextInputAction.next,
          onFieldSubmitted: (value) {
            _hba1cFocus.requestFocus();
          },
          decoration: util.inputBorder('血糖 (mg/dL)'),
        ),
        const SizedBox(height: 20),
        TextFormField(
          focusNode: _hba1cFocus,
          validator: util.nonEmptyValidator,
          onSaved: (newValue) {
            PredictDiabetesField().hba1c = double.parse(newValue!);
          },
          keyboardType: TextInputType.numberWithOptions(decimal: true),
          inputFormatters: const [util.UdoubleFormatter()],
          textInputAction: TextInputAction.done,
          decoration: util.inputBorder('HbA1c (%)'),
        ),
      ],
    );
  }
}
